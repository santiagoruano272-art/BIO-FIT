from django.shortcuts import render
from django.contrib.auth import login
from django.contrib.auth.models import User
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes # IMPORTANTE: Aquí está 'api_view'
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone

from apps.conexion.auth import register_user, login_user
from services.firebase_client import FirebaseClient

firebase = FirebaseClient()

# Vistas de plantillas
def landing_page(request): return render(request, 'landing.html')
def login_page(request): return render(request, 'users/login.html')
def registro_page(request): return render(request, 'users/registro.html')


class RegisterView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        # ── 1. Extraer TODOS los campos del formulario ──────────────────────
        email    = (request.data.get("email") or "").strip().lower()
        password = request.data.get("password", "")
        nombre   = (request.data.get("nombre") or "").strip()
        telefono = (request.data.get("telefono") or "").strip()
        nivel    = (request.data.get("nivel") or "principiante").strip().lower()
        gym_id   = request.data.get("gym_id")   # puede ser None para atletas sin gimnasio

        # ── 2. Validación mínima ────────────────────────────────────────────
        if not email or not password:
            return Response(
                {"error": "Email y contraseña son requeridos."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ── 3. Crear usuario en Firebase Auth ───────────────────────────────
        result = register_user(email, password)
        if "error" in result:
            print(f"[BIO-FIT] Error al crear usuario en Firebase Auth: {result['error']}")
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

        uid = result["uid"]

        # ── 4. Construir perfil completo para Firestore ─────────────────────
        perfil = {
            "uid":        uid,
            "email":      email,
            "rol":        "atleta",
            "is_active":  True,
            "nombre":     nombre,
            "telefono":   telefono,
            "nivel":      nivel,
            "updated_at": timezone.now(),
        }
        # Solo incluir gym_id si viene en la petición
        if gym_id:
            perfil["gym_id"] = gym_id

        # ── 5. Guardar perfil completo en Firestore ─────────────────────────
        try:
            firebase.save_user_profile(uid, perfil)
            print(f"[BIO-FIT] Perfil guardado OK — uid={uid} email={email} nombre={nombre}")
        except Exception as e:
            # El usuario ya existe en Firebase Auth pero no en Firestore.
            # Loguear y devolver error para que el cliente lo maneje.
            print(f"[BIO-FIT] ERROR guardando perfil en Firestore: {e}")
            return Response(
                {"error": "Usuario creado pero no se pudo guardar el perfil. Contacta soporte."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {"message": "Registrado correctamente.", "uid": uid, "email": email},
            status=status.HTTP_201_CREATED,
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    email    = request.data.get('email', '').strip()
    password = request.data.get('password', '')
    result   = login_user(email, password)

    if not result or "error" in result:
        return Response(result or {"error": "Error interno"}, status=status.HTTP_401_UNAUTHORIZED)

    # Bloqueo: contraseña provisional detectada
    if result.get("must_change_password"):
        request.session['uid_pending_password_change']   = result.get("uid")
        request.session['email_pending_password_change'] = email
        request.session.modified = True
        return Response(
            {
                "must_change_password": True,
                "redirect":             "/cambiar-password/",
                "error":                result["error"],
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    user, _ = User.objects.get_or_create(username=email, defaults={'email': email})

    request.session['user_uid'] = result["uid"]
    request.session['user_rol'] = result.get("rol")
    request.session['gym_id']   = result.get("gym_id")
    request.session.modified    = True

    login(request, user)
    return Response(result, status=status.HTTP_200_OK)