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


# ── RECUPERACIÓN DE CONTRASEÑA (CÓDIGO DE 6 DÍGITOS) ─────────────────────────

# Almacenamiento en memoria para rate limiting: { email: [timestamp, ...] }
_recovery_attempts: dict = {}
MAX_INTENTOS_POR_HORA = 3
CODIGO_EXPIRY_SECONDS = 1800  # 30 minutos


def _limpiar_intentos_expirados(email: str) -> None:
    """Elimina del registro los intentos que ya tienen más de 1 hora."""
    import time
    ahora = time.time()
    if email in _recovery_attempts:
        _recovery_attempts[email] = [t for t in _recovery_attempts[email] if ahora - t < 3600]


def verificar_limite_recuperacion(email: str) -> bool:
    """
    Retorna True si el usuario aún puede solicitar recuperación.
    Retorna False si ya superó el máximo de intentos en la última hora.
    """
    _limpiar_intentos_expirados(email)
    intentos = _recovery_attempts.get(email, [])
    return len(intentos) < MAX_INTENTOS_POR_HORA


def registrar_intento_recuperacion(email: str) -> None:
    """Registra un nuevo intento de recuperación para el email."""
    import time
    _limpiar_intentos_expirados(email)
    _recovery_attempts.setdefault(email, []).append(time.time())


def generar_codigo_recuperacion(uid: str) -> str | None:
    """
    Genera un código numérico de 6 dígitos criptográficamente seguro,
    lo persiste en Firestore con una marca de expiración (30 min)
    y retorna el código, o None si falla.
    """
    import time
    try:
        # Código de 6 dígitos: entre 100000 y 999999
        codigo = str(secrets.randbelow(900000) + 100000)
        expiry = time.time() + CODIGO_EXPIRY_SECONDS
        firebase.db.collection('users').document(uid).update({
            'reset_codigo':        codigo,
            'reset_codigo_expiry': expiry,
        })
        return codigo
    except Exception as e:
        logger.error(f"[BIO-FIT] Error generando código de recuperación para uid={uid}: {e}")
        return None


def enviar_correo_recuperacion(email: str, codigo: str) -> bool:
    """
    Envía el correo con el código de 6 dígitos usando el backend de
    correo configurado en Django (settings.EMAIL_*).
    Retorna True si el envío fue exitoso.
    """
    from django.core.mail import send_mail
    from django.conf import settings as dj_settings

    asunto = "BIO-FIT — Código para restablecer tu contraseña"
    cuerpo_texto = (
        f"Hola,\n\n"
        f"Recibimos una solicitud para restablecer la contraseña de tu cuenta BIO-FIT.\n\n"
        f"Tu código de verificación es:\n\n"
        f"  {codigo}\n\n"
        f"Este código es válido por 30 minutos. Ingrésalo en la página de recuperación.\n\n"
        f"Si no solicitaste este cambio, puedes ignorar este correo.\n\n"
        f"— El equipo de BIO-FIT"
    )
    cuerpo_html = f"""
    <div style="font-family:'DM Sans',Arial,sans-serif;background:#0b1628;padding:40px 0;min-height:100vh">
      <div style="max-width:460px;margin:0 auto;background:#111c30;border-radius:20px;
                  border:1px solid rgba(96,165,250,0.18);overflow:hidden;">
        <div style="height:6px;background:linear-gradient(90deg,rgba(96,165,250,0.95),rgba(96,165,250,0.05))"></div>
        <div style="padding:36px 36px 32px">
          <h2 style="color:#c4d4e8;font-size:1.3rem;margin:0 0 8px;font-family:'Syne',Arial,sans-serif">
            Restablece tu contraseña
          </h2>
          <p style="color:#5a7a9f;font-size:0.95rem;line-height:1.6;margin:0 0 24px">
            Usa el siguiente código para verificar tu identidad y crear una nueva contraseña.
            El código es válido durante <strong style="color:#8ba3c7">30 minutos</strong>.
          </p>
          <div style="text-align:center;margin:28px 0;">
            <span style="display:inline-block;padding:18px 36px;background:rgba(37,99,235,0.15);
                         border:2px solid rgba(96,165,250,0.4);border-radius:16px;
                         font-size:2.4rem;font-weight:800;letter-spacing:0.22em;
                         color:#93c5fd;font-family:'Syne',Arial,sans-serif;">
              {codigo}
            </span>
          </div>
          <p style="color:#3a5272;font-size:0.8rem;margin:24px 0 0;line-height:1.6">
            Si no solicitaste este cambio, puedes ignorar este correo con seguridad.
          </p>
        </div>
      </div>
    </div>
    """

    try:
        send_mail(
            subject        = asunto,
            message        = cuerpo_texto,
            from_email     = getattr(dj_settings, 'DEFAULT_FROM_EMAIL', 'noreply@biofit.com'),
            recipient_list = [email],
            html_message   = cuerpo_html,
            fail_silently  = False,
        )
        return True
    except Exception as e:
        logger.error(f"[BIO-FIT] Error enviando correo de recuperación a {email}: {e}")
        return False


def validar_codigo_recuperacion(email: str, codigo: str) -> dict | None:
    """
    Busca en Firestore el usuario con ese email y verifica que el
    código ingresado coincida y no haya expirado.
    Retorna el perfil (con 'uid') si es válido, None en caso contrario.
    """
    import time
    try:
        docs = (
            firebase.db.collection('users')
            .where('email', '==', email)
            .limit(1)
            .stream()
        )
        for doc in docs:
            perfil = doc.to_dict()
            codigo_guardado = perfil.get('reset_codigo', '')
            expiry          = perfil.get('reset_codigo_expiry', 0)

            if not codigo_guardado:
                logger.warning(f"[BIO-FIT] No hay código activo para {email}")
                return None
            if time.time() > expiry:
                logger.warning(f"[BIO-FIT] Código expirado para {email}")
                return None
            if not secrets.compare_digest(str(codigo_guardado), str(codigo)):
                logger.warning(f"[BIO-FIT] Código incorrecto para {email}")
                return None

            perfil['uid'] = doc.id
            return perfil

        return None
    except Exception as e:
        logger.error(f"[BIO-FIT] Error validando código de recuperación: {e}")
        return None


def aplicar_nueva_password(uid: str, nueva_password: str) -> bool:
    """
    Actualiza la contraseña en Firebase Auth y elimina el código de
    recuperación del perfil de Firestore para que no pueda reutilizarse.
    """
    try:
        firebase_auth.update_user(uid, password=nueva_password)
        firebase.db.collection('users').document(uid).update({
            'reset_codigo':        None,
            'reset_codigo_expiry': None,
        })
        logger.info(f"[BIO-FIT] Contraseña actualizada exitosamente para uid={uid}")
        return True
    except Exception as e:
        logger.error(f"[BIO-FIT] Error aplicando nueva contraseña para uid={uid}: {e}")
        return False