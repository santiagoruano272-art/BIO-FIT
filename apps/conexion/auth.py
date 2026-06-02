import secrets
import string
import requests
from firebase_admin import auth as firebase_auth
from django.conf import settings
from services.firebase_client import FirebaseClient

firebase = FirebaseClient()

# Roles válidos para administradores de gimnasio
ROLES_ADMIN = {'admin', 'gym_owner'}

# Mapa de normalización de roles legacy
ROL_MAP = {
    'gym_owner': 'admin',
}


# ── REGISTRO ─────────────────────────────────────────────────────────────────

def register_gym(gym_data: dict) -> dict:
    """
    Crea el usuario Firebase y el perfil del gimnasio en Firestore.
    El rol se guarda siempre como 'admin'.
    """
    user = None
    try:
        email    = gym_data['email'].strip().lower()
        password = generar_password_provisional()
        user     = firebase_auth.create_user(
            email=email,
            password=password,
            display_name=gym_data['nombre'],
        )

        gym_id = firebase.create_gym({**gym_data, 'owner_uid': user.uid})

        firebase.save_user_profile(user.uid, {
            'email':                email,
            'uid':                  user.uid,
            'rol':                  'admin',       # siempre 'admin', nunca 'gym_owner'
            'gym_id':               gym_id,
            'must_change_password': True,
        })

        return {"success": True, "uid": user.uid, "gym_id": gym_id}

    except Exception as e:
        return {"error": str(e)}


def register_user(email: str, password: str) -> dict:
    """Crea un usuario Firebase básico (atleta u otro rol)."""
    try:
        user = firebase_auth.create_user(email=email, password=password)
        return {"uid": user.uid, "email": email}
    except Exception as e:
        return {"error": str(e)}


# ── LOGIN ─────────────────────────────────────────────────────────────────────

def login_user(email: str, password: str) -> dict:
    """
    Autentica contra Firebase REST API y devuelve uid, rol normalizado,
    idToken y gym_id.

    El rol se normaliza con ROL_MAP para convertir valores legacy
    ('gym_owner' → 'admin') antes de devolverlos.
    """
    try:
        url  = (
            "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword"
            f"?key={settings.FIREBASE_API_KEY}"
        )
        resp = requests.post(
            url,
            json={"email": email, "password": password, "returnSecureToken": True},
        )
        data = resp.json()

        if "error" in data:
            return {"error": data["error"]["message"]}

        uid    = data["localId"]
        perfil = firebase.get_user_profile(uid)

        # Fallback: buscar en colección 'gimnasios' si el perfil no existe
        if not perfil:
            gym_docs = (
                firebase.db.collection('gimnasios')
                .where('email', '==', email)
                .limit(1)
                .stream()
            )
            for doc in gym_docs:
                gym_data = doc.to_dict()
                perfil = {
                    'uid':    uid,
                    'rol':    gym_data.get('rol', 'admin'),
                    'gym_id': doc.id,
                    'email':  gym_data.get('email'),
                }
                break

        if not perfil:
            return {"error": "Usuario no encontrado"}

        # Verificar si debe cambiar la contraseña provisional
        if perfil.get('must_change_password'):
            return {
                "must_change_password": True,
                "uid":                  uid,
                "error":                "Debes cambiar tu contraseña provisional antes de continuar.",
            }

        # Normalizar rol legacy antes de devolver
        rol_raw = perfil.get('rol', 'admin')
        rol     = ROL_MAP.get(rol_raw, rol_raw)

        return {
            "uid":     uid,
            "rol":     rol,
            "idToken": data["idToken"],
            "gym_id":  perfil.get("gym_id"),
        }

    except Exception as e:
        return {"error": str(e)}


# ── CAMBIO DE CONTRASEÑA ──────────────────────────────────────────────────────

def confirmar_cambio_password(uid: str) -> bool:
    """
    Marca el perfil del usuario como que ya no necesita cambiar contraseña.
    Devuelve True si la operación fue exitosa.
    """
    try:
        firebase.db.collection('usuarios').document(uid).update({
            'must_change_password': False,
        })
        return True
    except Exception as e:
        return False


# ── MIGRACIÓN ─────────────────────────────────────────────────────────────────

def migrar_rol_gym_owner(uid: str) -> bool:
    """
    Corrige el rol 'gym_owner' → 'admin' en el perfil de Firestore.

    Usar una sola vez por usuario afectado. Puede ejecutarse desde
    el shell de Django:

        from apps.conexion.auth import migrar_rol_gym_owner
        migrar_rol_gym_owner("<uid_del_admin>")
    """
    try:
        perfil = firebase.get_user_profile(uid)
        if perfil and perfil.get('rol') == 'gym_owner':
            firebase.db.collection('usuarios').document(uid).update({'rol': 'admin'})
            return True
        return False
    except Exception:
        return False


# ── UTILIDADES ────────────────────────────────────────────────────────────────

def generar_password_provisional() -> str:
    """Genera una contraseña provisional segura de 16 caracteres."""
    alphabet = string.ascii_letters + string.digits + string.punctuation
    while True:
        password = ''.join(secrets.choice(alphabet) for _ in range(16))
        # Garantizar al menos una mayúscula, minúscula, dígito y símbolo
        if (
            any(c.isupper() for c in password)
            and any(c.islower() for c in password)
            and any(c.isdigit() for c in password)
            and any(c in string.punctuation for c in password)
        ):
            return password