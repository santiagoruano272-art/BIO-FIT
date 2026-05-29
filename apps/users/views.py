from django.shortcuts import render
from django.contrib.auth import login
from django.contrib.auth.models import User
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes # IMPORTANTE: Aquí está 'api_view'
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

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
        email = request.data.get("email")
        password = request.data.get("password")
        if not email or not password:
            return Response({"error": "Datos incompletos"}, status=status.HTTP_400_BAD_REQUEST)
        result = register_user(email, password)
        if "error" in result:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        firebase.save_user_profile(result["uid"], {"email": email, "rol": "atleta", "is_active": True})
        return Response({"message": "Registrado"}, status=status.HTTP_201_CREATED)

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

    # Guardar toda la sesión con asignaciones explícitas (más confiable que .update())
    # gym_id es crítico: sin él get_admin_tenant() devuelve None y redirige al login
    request.session['user_uid'] = result["uid"]
    request.session['user_rol'] = result.get("rol")
    request.session['gym_id']   = result.get("gym_id")   # ← faltaba esta línea
    request.session.modified    = True                    # ← fuerza guardado en BD

    login(request, user)
    return Response(result, status=status.HTTP_200_OK)