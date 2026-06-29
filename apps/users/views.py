import logging
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout as django_logout
from django.contrib.auth.models import User
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.views.decorators.cache import never_cache

from apps.conexion.auth import register_user, login_user
from services.firebase_client import FirebaseClient

logger = logging.getLogger(__name__)
firebase = FirebaseClient()


# ── VISTAS DE PLANTILLAS ──────────────────────────────────────────────────────

@never_cache
def landing_page(request):
    """
    Muestra el Dashboard principal del atleta o administrador basándose en la sesión.
    Si no existe una sesión activa, redirige limpiamente al login.
    """
    if not request.session.get('user_uid'):
        return redirect('login')

    contexto = {}
    user_uid = request.session.get('user_uid')

    # Resolver el apodo o nombre del usuario en el servidor antes de renderizar
    nombre_mostrar = 'Atleta'
    if user_uid:
        try:
            perfil_usuario = firebase.get_user_profile(user_uid)
            if perfil_usuario:
                nombre_mostrar = (
                    perfil_usuario.get('sobrenombre')
                    or perfil_usuario.get('nombre')
                    or 'Atleta'
                )
        except Exception as e:
            print(f"[BIO-FIT] Error obteniendo perfil del usuario en landing: {e}")

    contexto['user_display_name'] = nombre_mostrar

    gym_id = request.session.get('gym_id')
    if gym_id:
        try:
            gym = firebase.get_gym_by_id(gym_id)
            if gym:
                contexto['gym_nombre']    = gym.get('nombre', gym_id)
                contexto['gym_ubicacion'] = gym.get('ubicacion', '')
            else:
                contexto['gym_nombre']    = None
                contexto['gym_ubicacion'] = None
        except Exception as e:
            print(f"[BIO-FIT] Error obteniendo gym en landing: {e}")
            contexto['gym_nombre']    = None
            contexto['gym_ubicacion'] = None
    else:
        contexto['gym_nombre']    = None
        contexto['gym_ubicacion'] = None
    
    # Obtener días seleccionados de la rutina
    selected_days = ['Lunes', 'Miércoles', 'Viernes']
    if user_uid:
        try:
            docs = firebase.get_user_routines(user_uid)
            if docs:
                user_inputs = docs[0].get('user_inputs', {})
                if user_inputs and user_inputs.get('nombres_dias'):
                    selected_days = user_inputs.get('nombres_dias', [])
        except Exception as e:
            print(f"[BIO-FIT] Error obteniendo días de la rutina: {e}")
    
    # Pasar los días al template (como JSON)
    import json
    contexto['selected_days_json'] = json.dumps(selected_days)
    
    return render(request, 'landing.html', contexto)


@never_cache
def login_page(request):
    """Renderiza de forma limpia la interfaz visual de inicio de sesión."""
    # Siempre destruir la sesión del servidor al llegar al login.
    # Esto cubre el caso donde Django reinicia pero db.sqlite3 aún
    # conserva la sesión anterior, evitando el redirect automático al dashboard.
    django_logout(request)
    return render(request, 'users/login.html')


@never_cache
def registro_page(request):
    """Renderiza de forma limpia la interfaz visual de registro."""
    if request.session.get('user_uid'):
        return redirect('landing')
    return render(request, 'users/registro.html')


# ── REGISTRO (API) ────────────────────────────────────────────────────────────

class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email    = (request.data.get('email') or '').strip().lower()
        password = request.data.get('password', '')
        nombre   = (request.data.get('nombre') or '').strip()
        telefono = (request.data.get('telefono') or '').strip()
        nivel    = (request.data.get('nivel') or 'principiante').strip().lower()
        gym_id   = request.data.get('gym_id')

        if not email or not password or not nombre:
            return Response(
                {'error': 'Todos los campos requeridos (email, contraseña, nombre) deben ser provistos.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = register_user(email, password)
        if 'error' in result:
            print(f"[BIO-FIT] Error al crear usuario en Firebase Auth: {result['error']}")
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

        uid = result.get('uid')
        if not uid:
            return Response(
                {'error': 'Firebase Auth no retornó un identificador de usuario válido.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        perfil = {
            'uid':        uid,
            'email':      email,
            'rol':        'atleta',
            'is_active':  True,
            'nombre':     nombre,
            'telefono':   telefono,
            'nivel':      nivel,
            'updated_at': timezone.now(),
        }
        if gym_id:
            perfil['gym_id'] = gym_id

        try:
            firebase.save_user_profile(uid, perfil)
            print(f"[BIO-FIT] Perfil guardado OK — uid={uid} email={email}")
        except Exception as e:
            print(f"[BIO-FIT] ERROR guardando perfil en Firestore: {e}")
            return Response(
                {'error': 'Usuario creado pero no se pudo inicializar el perfil en la base de datos.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {'message': 'Registrado correctamente.', 'uid': uid, 'email': email},
            status=status.HTTP_201_CREATED,
        )


# ── LOGIN (API) ───────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """
    Procesa las credenciales enviadas por login.js contra Firebase Auth
    y establece la sesión segura dentro del ecosistema de Django.
    """
    email    = request.data.get('email', '').strip().lower()
    password = request.data.get('password', '')
    
    # Intentar autenticación con Firebase
    result = login_user(email, password)

    # 1. Validar si Firebase retornó un error o respuesta vacía
    if not result or 'error' in result:
        return Response(
            result or {'error': 'Credenciales incorrectas o error de autenticación.'}, 
            status=status.HTTP_401_UNAUTHORIZED
        )

    # 2. Extraer el UID de forma segura usando .get() para evitar KeyError
    uid = result.get('uid')
    if not uid:
        return Response(
            {'error': 'El servicio de autenticación no retornó un UID de usuario válido.'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    # Manejo de bloqueo por cambio obligatorio de contraseña provisional
    if result.get('must_change_password'):
        request.session['uid_pending_password_change']   = uid
        request.session['email_pending_password_change'] = email
        request.session.modified = True
        return Response(
            {
                'must_change_password': True,
                'redirect':             '/cambiar-password/',
                'error':                result.get('error', 'Debe actualizar su contraseña provisional.'),
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    # 3. Autenticación e inicio de sesión local en Django
    user, _ = User.objects.get_or_create(username=email, defaults={'email': email})
    login(request, user)  # Django regenera de forma segura el ID de sesión aquí

    # 4. Asignación controlada de variables en la sesión del backend
    request.session['user_uid'] = uid
    request.session['user_rol'] = result.get('rol', 'atleta')
    request.session['gym_id']   = result.get('gym_id', None)
    request.session.modified    = True
    request.session.save()

    # 5. Respuesta estructurada para el cliente (login.js)
    return Response({
        'message': 'Login exitoso',
        'uid': uid,
        'rol': request.session['user_rol'],
        'gym_id': request.session['gym_id'],
        'token': result.get('idToken') or result.get('token')
    }, status=status.HTTP_200_OK)


# ── LOGOUT MANUAL (API) ───────────────────────────────────────────────────────

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
        logger.error("Error durante el proceso de logout: %s", e)
        return Response({'error': 'No se pudo cerrar la sesión correctamente.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ── AUTO-LOGOUT AL CERRAR PESTAÑA/NAVEGADOR (API) ────────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
def auto_logout_view(request):
    """
    Llamado automáticamente por sendBeacon() desde base.js cuando el usuario
    cierra la pestaña o el navegador. Destruye la sesión en el servidor
    de forma idéntica al logout manual, sin requerir autenticación previa
    (porque la cookie de sesión puede haber expirado justo al cerrar).
    """
    try:
        django_logout(request)
        return Response({'message': 'Sesión cerrada automáticamente.'}, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error("Error en auto-logout: %s", e)
        # Retornamos 200 siempre para que el navegador no reintente la solicitud
        return Response({'ok': True}, status=status.HTTP_200_OK)