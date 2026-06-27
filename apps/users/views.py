import logging
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout as django_logout  # <-- MODIFICADO: Añadido django_logout
from django.contrib.auth.models import User
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.views.decorators.cache import never_cache  # <-- MODIFICADO: Previene caché agresiva del HTML

from apps.conexion.auth import register_user, login_user
from services.firebase_client import FirebaseClient

logger = logging.getLogger(__name__)
firebase = FirebaseClient()


# ── VISTAS DE PLANTILLAS ──────────────────────────────────────────────────────

@never_cache  # <-- MODIFICADO: Evita que al dar botón "Atrás" tras cerrar sesión se siga viendo el dashboard
def landing_page(request):
    """
    FIX: ahora pasa el contexto del gimnasio al template para que la tarjeta
    central del dashboard muestre el nombre del gym o 'Desde casa'.
    También pasa los días seleccionados de la rutina.
    """
    if not request.session.get('user_uid'):
        return redirect('login')

    contexto = {}
    user_uid = request.session.get('user_uid')

    try:
        # Intentar obtener el perfil desde Firestore para renderizar dinámicamente en el servidor
        perfil = firebase.get_user_profile(user_uid)
        if perfil:
            contexto['user_display_name'] = perfil.get('sobrenombre') or perfil.get('nombre') or 'Atleta'
            
            # Obtener datos del gimnasio si está vinculado
            gym_id = request.session.get('gym_id') or perfil.get('gym_id')
            if gym_id:
                gym = firebase.get_gym_by_id(gym_id)
                if gym:
                    contexto['gym_nombre'] = gym.get('nombre')
            
            # Obtener datos de la rutina (músculos, días, etc.) si existen
            rutina_actual = perfil.get('rutina_actual') or {}
            if rutina_actual:
                contexto['rutina_musculos'] = ", ".join(rutina_actual.get('musculos_objetivo', []))
                contexto['rutina_dias'] = rutina_actual.get('dias_seleccionados', [])
    except Exception as e:
        logger.error(f"Error cargando datos en landing_page para uid {user_uid}: {e}")
        contexto['user_display_name'] = 'Atleta'

    return render(request, 'landing.html', contexto)


def login_page(request):
    """Renderiza la página de inicio de sesión."""
    if request.session.get('user_uid'):
        return redirect('landing')
    return render(request, 'login.html')


def registro_page(request):
    """Renderiza la página de registro."""
    if request.session.get('user_uid'):
        return redirect('landing')
    return render(request, 'registro.html')


# ── API DE CONEXIÓN Y AUTENTICACIÓN ──────────────────────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    email    = request.data.get('email', '').strip().lower()  # Normalizar a minúsculas
    password = request.data.get('password', '')
    result   = login_user(email, password)

    # 1. Validar de forma segura si el inicio de sesión falló o trae un error
    if not result or 'error' in result:
        return Response(result or {'error': 'Credenciales incorrectas o error de autenticación'}, status=status.HTTP_401_UNAUTHORIZED)

    # 2. Extraer el UID de forma segura usando .get()
    uid = result.get('uid')
    if not uid:
        return Response(
            {'error': 'El servicio de autenticación no devolvió un identificador de usuario válido (UID).'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    # Bloqueo: contraseña provisional
    if result.get('must_change_password'):
        request.session['uid_pending_password_change']   = uid
        request.session['email_pending_password_change'] = email
        request.session.modified = True
        return Response(
            {
                'must_change_password': True,
                'redirect':             '/cambiar-password/',
                'error':                result.get('error', 'Debe cambiar la contraseña provisional.'),
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    # 3. Autenticación en Django local
    user, _ = User.objects.get_or_create(username=email, defaults={'email': email})
    login(request, user)  # Django regenera el session ID aquí

    # 4. Guardar en sesión de forma segura sin peligro de KeyError
    request.session['user_uid'] = uid
    request.session['user_rol'] = result.get('rol', 'atleta')
    request.session['gym_id']   = result.get('gym_id', None)
    request.session.modified    = True
    request.session.save()

    # 5. Respuesta limpia y estructurada para tu JavaScript (login.js)
    return Response({
        'message': 'Login exitoso',
        'uid': uid,
        'rol': request.session['user_rol'],
        'gym_id': request.session['gym_id'],
        'token': result.get('idToken') or result.get('token')
    }, status=status.HTTP_200_OK)
class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email', '').strip().lower()
        password = request.data.get('password', '')
        nombre = request.data.get('nombre', '').strip()

        if not email or not password or not nombre:
            return Response({'error': 'Todos los campos son obligatorios.'}, status=status.HTTP_400_BAD_REQUEST)

        result = register_user(email, password, nombre)
        if 'error' in result:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

        return Response(result, status=status.HTTP_201_CREATED)


# ── NUEVA VISTA: CONTROLADOR DE CIERRE DE SESIÓN ──────────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
def logout_view(request):
    """
    Destruye por completo la sesión activa en el servidor de Django 
    y limpia la cookie 'sessionid' en el navegador del cliente.
    """
    try:
        django_logout(request)
        return Response({'message': 'Sesión destruida exitosamente.'}, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error("Error crítico ejecutando logout_view: %s", e)
        return Response(
            {'error': 'Error interno en el servidor al intentar cerrar sesión.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )