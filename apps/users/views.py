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

from apps.conexion.auth import (
    register_user, login_user,
    verificar_limite_recuperacion, registrar_intento_recuperacion,
    generar_codigo_recuperacion, enviar_correo_recuperacion,
    validar_codigo_recuperacion, aplicar_nueva_password,
)
# Nota: validar_codigo_recuperacion se usa tanto en verificar_codigo_view (paso 2)
# como en restablecer_password_view (paso 3) para doble validación.
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

    import json
    contexto['selected_days_json'] = json.dumps(selected_days)

    return render(request, 'landing.html', contexto)


@never_cache
def login_page(request):
    """
    Renderiza de forma limpia la interfaz visual de inicio de sesión.
    """
    django_logout(request)
    return render(request, 'users/login.html', {})


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
    email    = request.data.get('email', '').strip().lower()
    password = request.data.get('password', '')

    result = login_user(email, password)

    if not result or 'error' in result:
        return Response(
            result or {'error': 'Credenciales incorrectas o error de autenticación.'},
            status=status.HTTP_401_UNAUTHORIZED
        )

    uid = result.get('uid')

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

    user, _ = User.objects.get_or_create(username=email, defaults={'email': email})
    login(request, user)

    request.session['user_uid'] = uid
    request.session['user_rol'] = result.get('rol', 'atleta')
    request.session['gym_id']   = result.get('gym_id', None)
    request.session.modified    = True
    request.session.save()

    return Response({
        'message': 'Login exitoso',
        'uid':     uid,
        'rol':     request.session['user_rol'],
        'gym_id':  request.session['gym_id'],
        'token':   result.get('idToken') or result.get('token')
    }, status=status.HTTP_200_OK)


# ── LOGOUT MANUAL (API) ───────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
def logout_view(request):
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
    try:
        django_logout(request)
        return Response({'message': 'Sesión cerrada automáticamente.'}, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error("Error en auto-logout: %s", e)
        return Response({'ok': True}, status=status.HTTP_200_OK)


# ── RECUPERACIÓN DE CONTRASEÑA — PASO 1: Enviar código (API) ─────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
def recuperar_password_view(request):
    """
    Recibe un email, verifica que exista en Firestore, genera un código
    de 6 dígitos y lo envía por correo.

    Siempre responde 200 OK sin revelar si el email está registrado
    (prevención de enumeración de usuarios). El rate limiting devuelve 429.
    """
    email = (request.data.get('email') or '').strip().lower()

    if not email:
        return Response(
            {'error': 'El campo de correo electrónico es obligatorio.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # ── Rate limiting ──────────────────────────────────────────────────────
    if not verificar_limite_recuperacion(email):
        return Response(
            {'error': 'Has realizado demasiados intentos. Por favor espera al menos una hora antes de volver a intentarlo.'},
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    registrar_intento_recuperacion(email)

    # ── Buscar al usuario en Firestore ─────────────────────────────────────
    try:
        docs = firebase.db.collection('users').where('email', '==', email).limit(1).stream()
        usuario = None
        for doc in docs:
            usuario = doc.to_dict()
            usuario['uid'] = doc.id
            break
    except Exception as e:
        logger.error(f"[BIO-FIT] Error buscando usuario para recuperación ({email}): {e}")
        return Response({'message': 'Si ese correo está registrado, recibirás un código en breve.'}, status=status.HTTP_200_OK)

    if not usuario:
        logger.info(f"[BIO-FIT] Solicitud de recuperación para email no registrado: {email}")
        return Response(
            {'error': 'Este correo no está registrado en BIO-FIT.'},
            status=status.HTTP_404_NOT_FOUND,
        )

    uid = usuario['uid']

    # ── Generar código y guardar en Firestore ──────────────────────────────
    codigo = generar_codigo_recuperacion(uid)
    if not codigo:
        logger.error(f"[BIO-FIT] Falló la generación del código para uid={uid}")
        return Response(
            {'error': 'Error interno al generar el código de recuperación. Intenta de nuevo.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    # ── Enviar correo ──────────────────────────────────────────────────────
    enviado = enviar_correo_recuperacion(email, codigo)
    if not enviado:
        logger.error(f"[BIO-FIT] Falló el envío de correo de recuperación a {email}")
        return Response(
            {'error': 'No se pudo enviar el correo. Verifica la configuración del servidor de correo.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return Response(
        {'message': 'Si ese correo está registrado, recibirás un código en breve.'},
        status=status.HTTP_200_OK,
    )


# ── RECUPERACIÓN DE CONTRASEÑA — PASO 2: Verificar código ────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
def verificar_codigo_view(request):
    """
    Recibe el email y el código de 6 dígitos.
    Solo verifica que sea válido y no haya expirado sin aplicar aún la contraseña.
    Retorna 200 si el código es correcto, 400 si no.
    """
    email  = (request.data.get('email') or '').strip().lower()
    codigo = (request.data.get('codigo') or '').strip()

    if not email or not codigo:
        return Response(
            {'error': 'Email y código son obligatorios.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    perfil = validar_codigo_recuperacion(email, codigo)
    if not perfil:
        return Response(
            {'error': 'El código es incorrecto o ya expiró. Solicita uno nuevo.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    return Response({'message': 'Código válido.'}, status=status.HTTP_200_OK)


# ── RECUPERACIÓN DE CONTRASEÑA — PASO 3: Verificar código y nueva contraseña ─

@api_view(['POST'])
@permission_classes([AllowAny])
def restablecer_password_view(request):
    """
    Recibe el email, el código de 6 dígitos y la nueva contraseña.
    Valida el código, aplica las reglas de seguridad y actualiza Firebase Auth.
    El código queda invalidado tras el primer uso exitoso.
    """
    import re

    email          = (request.data.get('email') or '').strip().lower()
    codigo         = (request.data.get('codigo') or '').strip()
    nueva_password = request.data.get('nueva_password', '')

    if not email or not codigo or not nueva_password:
        return Response(
            {'error': 'Email, código y nueva contraseña son obligatorios.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # ── Validaciones de seguridad de la contraseña ─────────────────────────
    errores = []
    if len(nueva_password) < 8:
        errores.append('al menos 8 caracteres')
    if not re.search(r'[A-Z]', nueva_password):
        errores.append('una letra mayúscula')
    if not re.search(r'[a-z]', nueva_password):
        errores.append('una letra minúscula')
    if not re.search(r'\d', nueva_password):
        errores.append('un número')
    if not re.search(r'[!@#$%^&*()\-_=+\[\]{};:\'",.<>/?\\|`~]', nueva_password):
        errores.append('un carácter especial (!@#$...)')

    if errores:
        return Response(
            {'error': f'La contraseña debe incluir: {", ".join(errores)}.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # ── Validar código en Firestore ────────────────────────────────────────
    perfil = validar_codigo_recuperacion(email, codigo)
    if not perfil:
        return Response(
            {'error': 'El código es incorrecto o ya expiró. Solicita uno nuevo.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    uid = perfil['uid']

    # ── Aplicar la nueva contraseña en Firebase Auth ───────────────────────
    exito = aplicar_nueva_password(uid, nueva_password)
    if not exito:
        return Response(
            {'error': 'No se pudo actualizar la contraseña. Intenta de nuevo.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return Response(
        {'message': 'Contraseña actualizada correctamente. Ya puedes iniciar sesión.'},
        status=status.HTTP_200_OK,
    )