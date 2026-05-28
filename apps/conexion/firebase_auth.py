import logging
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from firebase_admin import auth
from services.firebase_client import FirebaseClient

logger = logging.getLogger(__name__)
firebase = FirebaseClient()

class FirebaseUser:
    def __init__(self, uid: str, email: str, perfil: dict):
        self.uid           = uid
        self.email         = email
        self.nombre        = perfil.get('nombre', 'Usuario')
        self.nivel         = perfil.get('nivel', 'principiante')
        self.objetivo      = perfil.get('objetivo', None)
        self.is_active     = perfil.get('is_active', True)
        self.is_authenticated = True
        self.is_anonymous  = False
        self.is_staff      = False

    def __str__(self):
        return f"FirebaseUser(uid={self.uid}, email={self.email})"

class FirebaseAuthentication(BaseAuthentication):
    def authenticate(self, request):
        id_token = self._extraer_token(request)
        if not id_token:
            return None 

        decoded_token = self._verificar_token(id_token)
        uid   = decoded_token.get('uid')
        email = decoded_token.get('email', '')

        if not uid:
            raise AuthenticationFailed('Token no contiene UID válido')

        perfil = self._cargar_perfil(uid)
        user   = FirebaseUser(uid=uid, email=email, perfil=perfil)

        if not user.is_active:
            raise AuthenticationFailed('Usuario desactivado')

        return (user, decoded_token)

    def _extraer_token(self, request) -> str | None:
        auth_header = request.META.get('HTTP_AUTHORIZATION') or request.headers.get('Authorization')
        if not auth_header: return None
        partes = auth_header.split()
        if len(partes) != 2 or partes[0].lower() != 'bearer': return None
        return partes[1]

    def _verificar_token(self, id_token: str) -> dict:
        try:
            return auth.verify_id_token(id_token)
        except Exception:
            raise AuthenticationFailed('Token inválido o expirado')

    def _cargar_perfil(self, uid: str) -> dict:
        try:
            return firebase.get_user_profile(uid) or {}
        except Exception:
            return {}

    # NUEVO MÉTODO PARA CARGAR HISTORIAL
    def get_user_routines(self, uid: str):
        try:
            # Accedemos a la sub-colección dentro del documento del usuario
            docs = firebase.db.collection('users').document(uid).collection('rutinas_generadas').stream()
            return [{"id": doc.id, **doc.to_dict()} for doc in docs]
        except Exception as e:
            logger.error(f"Error cargando rutinas: {e}")
            return []