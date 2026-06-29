import secrets
import string
import requests
import logging
from firebase_admin import auth as firebase_auth
from django.conf import settings
from services.firebase_client import FirebaseClient

# Configuración
logger = logging.getLogger(__name__)
firebase = FirebaseClient()

# Definición de roles
ROLES_ADMIN = {'admin', 'gym_owner'}
ROL_MAP = {'gym_owner': 'admin'}

# ── FUNCIONES PRINCIPALES ─────────────────────────────────────────────────────

def register_user(email: str, password: str, nombre: str = "") -> dict:
    """Crea un usuario Firebase básico."""
    try:
        user = firebase_auth.create_user(email=email, password=password)
        firebase.save_user_profile(user.uid, {
            'email': email,
            'uid': user.uid,
            'rol': 'atleta',
            'nombre': nombre
        })
        return {'uid': user.uid, 'email': email}
    except Exception as e:
        logger.error(f"Error en register_user: {e}")
        return {'error': str(e)}

def register_gym(gym_data: dict) -> dict:
    """Crea el usuario Firebase y el perfil del gimnasio."""
    try:
        email = gym_data['email'].strip().lower()
        password = generar_password_provisional()
        user = firebase_auth.create_user(
            email=email,
            password=password,
            display_name=gym_data['nombre'],
        )
        gym_id = firebase.create_gym({**gym_data, 'owner_uid': user.uid})
        firebase.save_user_profile(user.uid, {
            'email': email,
            'uid': user.uid,
            'rol': 'admin',
            'gym_id': gym_id,
            'must_change_password': True,
        })
        return {'success': True, 'uid': user.uid, 'gym_id': gym_id}
    except Exception as e:
        return {'error': str(e)}

def login_user(email: str, password: str) -> dict:
    """Autentica contra Firebase."""
    try:
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={settings.FIREBASE_API_KEY}"
        resp = requests.post(
            url,
            json={'email': email, 'password': password, 'returnSecureToken': True},
            timeout=10
        )
        data = resp.json()
        if 'error' in data:
            return {'error': data['error']['message']}
        
        uid = data['localId']
        perfil = firebase.get_user_profile(uid)
        
        # Si no hay perfil, devolvemos lo mínimo
        if not perfil:
            perfil = {'rol': 'atleta', 'gym_id': None}
            
        return {
            'uid': uid,
            'rol': ROL_MAP.get(perfil.get('rol', 'atleta'), perfil.get('rol', 'atleta')),
            'idToken': data['idToken'],
            'gym_id': perfil.get('gym_id'),
        }
    except Exception as e:
        return {'error': f"Error interno: {str(e)}"}

# ── UTILIDADES ────────────────────────────────────────────────────────────────

def generar_password_provisional() -> str:
    alphabet = string.ascii_letters + string.digits + string.punctuation
    while True:
        password = ''.join(secrets.choice(alphabet) for _ in range(16))
        if any(c.isupper() for c in password) and any(c.islower() for c in password) and any(c.isdigit() for c in password):
            return password

def confirmar_cambio_password(uid: str) -> bool:
    try:
        firebase.db.collection('users').document(uid).update({'must_change_password': False})
        return True
    except:
        return False