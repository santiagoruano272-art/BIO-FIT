from firebase_admin import auth as firebase_auth
from services.firebase_client import FirebaseClient
import requests
from django.conf import settings

firebase = FirebaseClient()

# =========================================
# REGISTRO DE USUARIO
# =========================================

def register_user(email: str, password: str) -> dict:
    user = None
    try:
        # 1. Crear en Firebase Auth
        user = firebase_auth.create_user(
            email=email,
            password=password
        )

        # 2. Guardar perfil en Firestore → colección 'users'
        firebase.save_user_profile(user.uid, {
            'email':     user.email,
            'uid':       user.uid,
            'nombre':    '',
            'nivel':     'principiante',
            'is_active': True,
        })

        return {"uid": user.uid, "email": user.email}

    except Exception as e:
        # Rollback: eliminar de Auth si Firestore falló
        if user:
            try:
                firebase_auth.delete_user(user.uid)
            except Exception:
                pass
        return {"error": str(e)}

# =========================================
# LOGIN (FIREBASE REST API)
# =========================================

def login_user(email: str, password: str) -> dict:
    try:
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={settings.FIREBASE_API_KEY}"

        response = requests.post(url, json={
            "email": email,
            "password": password,
            "returnSecureToken": True
        })

        data = response.json()

        if "error" in data:
            return {"error": data["error"]["message"]}

        return {
            "idToken":      data["idToken"],
            "refreshToken": data["refreshToken"],
            "uid":          data["localId"]
        }

    except Exception as e:
        return {"error": str(e)}

# =========================================
# VERIFICAR TOKEN
# =========================================

def verify_token(id_token: str) -> dict:
    try:
        decoded_token = firebase_auth.verify_id_token(id_token)
        return {
            "uid":   decoded_token.get("uid"),
            "email": decoded_token.get("email")
        }
    except firebase_auth.ExpiredIdTokenError:
        return {"error": "Token expirado"}
    except firebase_auth.InvalidIdTokenError:
        return {"error": "Token inválido"}
    except Exception as e:
        return {"error": str(e)}

# =========================================
# OBTENER USUARIO POR UID
# =========================================

def get_user(uid: str) -> dict:
    try:
        user = firebase_auth.get_user(uid)
        return {"uid": user.uid, "email": user.email}
    except Exception as e:
        return {"error": str(e)}