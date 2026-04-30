# =========================================
# AUTH.PY - MANEJO DE AUTENTICACIÓN FIREBASE
# =========================================

import requests
from django.conf import settings
from firebase_admin import auth as firebase_auth


# =========================================
# REGISTRO DE USUARIO (FIREBASE AUTH)
# =========================================

def register_user(email: str, password: str) -> dict:
    """
    Crea un usuario en Firebase Authentication.
    
    Retorna:
        dict: {uid, email}
    """
    try:
        user = firebase_auth.create_user(
            email=email,
            password=password
        )

        return {
            "uid": user.uid,
            "email": user.email
        }

    except Exception as e:
        return {"error": str(e)}


# =========================================
# LOGIN (USANDO FIREBASE REST API)
# =========================================

def login_user(email: str, password: str) -> dict:
    """
    Inicia sesión usando Firebase REST API.
    
    Retorna:
        idToken, refreshToken, uid
    """
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
            "idToken": data["idToken"],
            "refreshToken": data["refreshToken"],
            "uid": data["localId"]
        }

    except Exception as e:
        return {"error": str(e)}


# =========================================
# VERIFICAR TOKEN (BACKEND)
# =========================================

def verify_token(id_token: str) -> dict:
    """
    Verifica un token de Firebase.
    
    Retorna:
        datos del usuario decodificados
    """
    try:
        decoded_token = firebase_auth.verify_id_token(id_token)

        return {
            "uid": decoded_token.get("uid"),
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
    """
    Obtiene datos de usuario desde Firebase Auth
    """
    try:
        user = firebase_auth.get_user(uid)

        return {
            "uid": user.uid,
            "email": user.email
        }

    except Exception as e:
        return {"error": str(e)}