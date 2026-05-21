from firebase_admin import auth as firebase_auth
from services.firebase_client import FirebaseClient
import requests
from django.conf import settings

firebase = FirebaseClient()

# =========================================================================
# REGISTRO DE USUARIO CON CONTROL DE ROLES Y GIMNASIOS (MULTI-TENANCY)
# =========================================================================
def register_user(email: str, password: str, rol: str = 'atleta', gym_id: str = None) -> dict:
    user = None
    try:
        roles_validos = ['atleta', 'entrenador', 'admin']
        if rol not in roles_validos:
            return {"error": f"Rol inválido. Opciones: {', '.join(roles_validos)}"}

        # Si el rol es administrador, el ID del gimnasio es obligatorio
        if rol == 'admin' and not gym_id:
            return {"error": "El identificador de gimnasio (gym_id) es obligatorio para el rol administrador."}

        # 1. Crear usuario en Firebase Auth
        user = firebase_auth.create_user(
            email=email,
            password=password
        )

        # 2. Estructurar el perfil en Firestore
        profile_data = {
            'email':     user.email,
            'uid':       user.uid,
            'nivel':     'principiante',
            'rol':       rol,
            'is_active': True,
            'gym_id':    gym_id if rol == 'admin' else None  # Aislamiento de datos
        }

        firebase.save_user_profile(user.uid, profile_data)

        return {"uid": user.uid, "email": user.email, "rol": rol, "gym_id": profile_data['gym_id']}

    except Exception as e:
        if user:
            try:
                firebase_auth.delete_user(user.uid)
            except Exception:
                pass
        return {"error": str(e)}


# =========================================================================
# INICIO DE SESIÓN CON EXTRACCIÓN DE PARÁMETROS DE FILTRADO
# =========================================================================
def login_user(email: str, password: str) -> dict:
    try:
        url = (
            f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword"
            f"?key={settings.FIREBASE_API_KEY}"
        )

        response = requests.post(url, json={
            "email": email,
            "password": password,
            "returnSecureToken": True
        })

        data = response.json()

        if "error" in data:
            return {"error": data["error"]["message"]}

        uid = data["localId"]

        # Recuperar perfil extendido de Firestore
        rol = "atleta"
        gym_id = None
        try:
            perfil = firebase.get_user_profile(uid)
            if perfil:
                rol = perfil.get("rol", "atleta")
                gym_id = perfil.get("gym_id", None)
        except Exception as e:
            print(f"[BIO-FIT Warning] No se pudo mapear la metadata para {uid}: {e}")

        return {
            "idToken":      data["idToken"],
            "refreshToken": data["refreshToken"],
            "uid":          uid,
            "rol":          rol,
            "gym_id":       gym_id
        }

    except Exception as e:
        return {"error": str(e)}


def verify_token(id_token: str) -> dict:
    try:
        decoded_token = firebase_auth.verify_id_token(id_token)
        return {
            "uid":   decoded_token.get("uid"),
            "email": decoded_token.get("email"),
        }
    except firebase_auth.ExpiredIdTokenError:
        return {"error": "Token expirado"}
    except firebase_auth.InvalidIdTokenError:
        return {"error": "Token inválido"}
    except Exception as e:
        return {"error": str(e)}