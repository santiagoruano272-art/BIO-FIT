from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.models import User
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone

from apps.conexion.auth import register_user, login_user
from services.firebase_client import FirebaseClient

firebase = FirebaseClient()


# ── VISTAS DE PLANTILLAS ──────────────────────────────────────────────────────

def landing_page(request):
    """
    FIX: ahora pasa el contexto del gimnasio al template para que la tarjeta
    central del dashboard muestre el nombre del gym o 'Desde casa'.
    También pasa los días seleccionados de la rutina.
    """
    # FIX: si no hay sesión activa, no se debe mostrar el dashboard del atleta.
    # Antes, al no existir 'user_rol' en sesión, el template caía en el {% else %}
    # de landing.html (que es justamente el dashboard del atleta), dando la
    # apariencia de estar logueado sin estarlo.
    if not request.session.get('user_uid'):
        return redirect('login')

    contexto = {}

    user_uid = request.session.get('user_uid')

    # FIX: resolver el apodo/nombre del usuario en el servidor, ANTES de
    # renderizar. Antes el template siempre pintaba "Atleta" fijo y
    # landing.js lo reemplazaba unos segundos después al llegar la
    # respuesta de /api/perfil/. Ahora el HTML ya llega con el nombre
    # correcto desde el primer render, sin parpadeo.
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
        # Intentar obtener el nombre del gimnasio desde Firestore (con caché)
        try:
            gym = firebase.get_gym_by_id(gym_id)
            if gym:
                contexto['gym_nombre']    = gym.get('nombre', gym_id)
                contexto['gym_ubicacion'] = gym.get('ubicacion', '')
            else:
                # gym_id huérfano — no existe en Firestore
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


def login_page(request):
    return render(request, 'users/login.html')


def registro_page(request):
    return render(request, 'users/registro.html')


# ── REGISTRO ──────────────────────────────────────────────────────────────────

class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        # 1. Extraer campos del formulario
        email    = (request.data.get('email') or '').strip().lower()
        password = request.data.get('password', '')
        nombre   = (request.data.get('nombre') or '').strip()
        telefono = (request.data.get('telefono') or '').strip()
        nivel    = (request.data.get('nivel') or 'principiante').strip().lower()
        gym_id   = request.data.get('gym_id')  # puede ser None

        # 2. Validación mínima
        if not email or not password:
            return Response(
                {'error': 'Email y contraseña son requeridos.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 3. Crear usuario en Firebase Auth
        result = register_user(email, password)
        if 'error' in result:
            print(f"[BIO-FIT] Error al crear usuario en Firebase Auth: {result['error']}")
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

        uid = result['uid']

        # 4. Construir perfil completo para Firestore
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

        # 5. Guardar perfil en Firestore
        try:
            firebase.save_user_profile(uid, perfil)
            print(f"[BIO-FIT] Perfil guardado OK — uid={uid} email={email} nombre={nombre}")
        except Exception as e:
            print(f"[BIO-FIT] ERROR guardando perfil en Firestore: {e}")
            return Response(
                {'error': 'Usuario creado pero no se pudo guardar el perfil. Contacta soporte.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {'message': 'Registrado correctamente.', 'uid': uid, 'email': email},
            status=status.HTTP_201_CREATED,
        )


# ── LOGIN ─────────────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    email    = request.data.get('email', '').strip().lower()  # FIX: normalizar a minúsculas
    password = request.data.get('password', '')
    result   = login_user(email, password)

    if not result or 'error' in result:
        return Response(result or {'error': 'Error interno'}, status=status.HTTP_401_UNAUTHORIZED)

    # Bloqueo: contraseña provisional
    if result.get('must_change_password'):
        request.session['uid_pending_password_change']   = result.get('uid')
        request.session['email_pending_password_change'] = email
        request.session.modified = True
        return Response(
            {
                'must_change_password': True,
                'redirect':             '/cambiar-password/',
                'error':                result['error'],
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    user, _ = User.objects.get_or_create(username=email, defaults={'email': email})

    login(request, user)  # Django regenera el session ID aquí

    # FIX: guardar DESPUÉS de login() para que no se pierdan con el nuevo session ID
    request.session['user_uid'] = result['uid']
    request.session['user_rol'] = result.get('rol')
    request.session['gym_id']   = result.get('gym_id')
    request.session.modified    = True
    request.session.save()

    return Response(result, status=status.HTTP_200_OK)