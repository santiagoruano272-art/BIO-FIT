import logging
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from firebase_admin import auth
from services.firebase_client import FirebaseClient

logger = logging.getLogger(__name__)

firebase = FirebaseClient()


# ── Modelo de usuario autenticado ────────────────────────────

class FirebaseUser:
    """
    Representa al usuario autenticado en cada request.
    Compatible con DRF y con request.user en las vistas.
    """

    def __init__(self, uid: str, email: str, perfil: dict):
        self.uid           = uid
        self.email         = email
        self.nombre        = perfil.get('nombre', 'Usuario')
        self.nivel         = perfil.get('nivel', 'principiante')
        self.objetivo      = perfil.get('objetivo', None)
        self.is_active     = perfil.get('is_active', True)
        self.is_authenticated = True

        # Compatibilidad mínima con Django
        self.is_anonymous  = False
        self.is_staff      = False

    def __str__(self):
        return f"FirebaseUser(uid={self.uid}, email={self.email}, nivel={self.nivel})"

    def tiene_perfil_completo(self) -> bool:
        """Verifica si el usuario completó su perfil de fitness."""
        return bool(self.nivel and self.objetivo)


# ── Autenticación principal 

class FirebaseAuthentication(BaseAuthentication):
    """
    Autenticación personalizada con Firebase JWT para DRF.

    Flujo:
    1. Extrae el Bearer token del header Authorization
    2. Verifica el token con Firebase Auth
    3. Carga el perfil del usuario desde Firestore
    4. Retorna un FirebaseUser con los datos del perfil
    """

    def authenticate(self, request):
        id_token = self._extraer_token(request)

        if not id_token:
            return None  # DRF probará otros backends si existen

        decoded_token = self._verificar_token(id_token)

        uid   = decoded_token.get('uid')
        email = decoded_token.get('email', '')

        if not uid:
            raise AuthenticationFailed('Token no contiene UID válido')

        perfil = self._cargar_perfil(uid)
        user   = FirebaseUser(uid=uid, email=email, perfil=perfil)

        if not user.is_active:
            raise AuthenticationFailed('Usuario desactivado')

        logger.info(f"Autenticación exitosa: {user}")
        return (user, decoded_token)

    def authenticate_header(self, request):
        """Indica a DRF que este backend usa Bearer tokens."""
        return 'Bearer realm="Firebase"'

    # ── Helpers privados 

    def _extraer_token(self, request) -> str | None:
        """Extrae y valida el formato del header Authorization."""
        auth_header = (
            request.META.get('HTTP_AUTHORIZATION')
            or request.headers.get('Authorization')
        )

        if not auth_header:
            return None

        partes = auth_header.split()

        if len(partes) != 2:
            raise AuthenticationFailed(
                'Formato de token inválido. Use: Bearer <token>'
            )

        if partes[0].lower() != 'bearer':
            raise AuthenticationFailed(
                'Tipo de autenticación no soportado. Use: Bearer'
            )

        return partes[1]

    def _verificar_token(self, id_token: str) -> dict:
        """Verifica el token JWT con Firebase Auth."""
        try:
            return auth.verify_id_token(id_token)

        except auth.InvalidIdTokenError:
            logger.warning("Token Firebase inválido recibido")
            raise AuthenticationFailed('Token inválido')

        except auth.ExpiredIdTokenError:
            logger.warning("Token Firebase expirado recibido")
            raise AuthenticationFailed('Token expirado. Por favor inicia sesión nuevamente')

        except auth.RevokedIdTokenError:
            logger.warning("Token Firebase revocado")
            raise AuthenticationFailed('Token revocado. Por favor inicia sesión nuevamente')

        except Exception as e:
            logger.error(f"Error inesperado verificando token: {e}")
            raise AuthenticationFailed('Error al verificar el token')

    def _cargar_perfil(self, uid: str) -> dict:
        """
        Carga el perfil del usuario desde Firestore.
        Si no existe, retorna un dict vacío (perfil nuevo).
        """
        try:
            perfil = firebase.get_user_profile(uid)

            if perfil is None:
                logger.info(f"Usuario nuevo sin perfil: {uid}")
                return {}

            return perfil

        except Exception as e:
            logger.error(f"Error cargando perfil de {uid}: {e}")
            return {}