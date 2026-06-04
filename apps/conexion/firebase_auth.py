import logging
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from firebase_admin import auth
from services.firebase_client import FirebaseClient

logger = logging.getLogger(__name__)
firebase = FirebaseClient()


class FirebaseUser:
    """
    Objeto usuario compatible con Django para autenticación via Firebase.
    FIX: agregados has_perm() y has_module_perms() requeridos por el
    middleware de Django y el panel de administración.
    """
    def __init__(self, uid: str, email: str, perfil: dict):
        self.uid              = uid
        self.email            = email
        self.nombre           = perfil.get('nombre', 'Usuario')
        self.nivel            = perfil.get('nivel', 'principiante')
        self.objetivo         = perfil.get('objetivo', None)
        self.is_active        = perfil.get('is_active', True)
        self.is_authenticated = True
        self.is_anonymous     = False
        self.is_staff         = False

    # FIX: métodos requeridos por Django — sin estos el middleware
    # puede lanzar AttributeError en vistas protegidas o en admin.
    def has_perm(self, perm, obj=None) -> bool:
        return False

    def has_module_perms(self, app_label: str) -> bool:
        return False

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
        auth_header = (
            request.META.get('HTTP_AUTHORIZATION')
            or request.headers.get('Authorization')
        )
        if not auth_header:
            return None
        partes = auth_header.split()
        if len(partes) != 2 or partes[0].lower() != 'bearer':
            return None
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

    def get_user_routines(self, uid: str) -> list:
        """Carga el historial de rutinas del usuario desde Firestore."""
        try:
            return firebase.get_user_routines(uid)
        except Exception as e:
            logger.error("Error cargando rutinas de %s: %s", uid, e)
            return []