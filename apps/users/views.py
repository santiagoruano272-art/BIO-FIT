from django.shortcuts import render
from django.contrib.auth import login
from django.contrib.auth.models import User
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from apps.conexion.auth import register_user, login_user
from services.firebase_client import FirebaseClient

firebase = FirebaseClient()

# =========================================
# VISTAS DE PLANTILLAS HTML
# =========================================
def landing_page(request):
    return render(request, 'landing.html')

def login_page(request):
    return render(request, 'users/login.html')

def registro_page(request):
    return render(request, 'users/registro.html')

# =========================================
# REGISTRO (API)
# =========================================
class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email    = request.data.get("email")
        password = request.data.get("password")
        nombre   = request.data.get("nombre", "")
        telefono = request.data.get("telefono", "")
        gym_id   = request.data.get("gym_id")   # None si eligió "desde casa"

        if not email or not password:
            return Response(
                {"error": "Email y password son requeridos"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 1. Crea el usuario en Firebase Auth
        result = register_user(email, password)

        if "error" in result:
            return Response(
                {"error": result["error"]},
                status=status.HTTP_400_BAD_REQUEST
            )

        uid = result["uid"]

        # 2. Guarda el perfil completo en Firestore, incluyendo gym_id
        perfil = {
            "email":    email,
            "nombre":   nombre,
            "telefono": telefono,
            "gym_id":   gym_id,   # puede ser None (entrena en casa) o el ID del gimnasio
            "rol":      "atleta",
            "is_active": True,
        }
        firebase.save_user_profile(uid, perfil)

        return Response({
            "uid":     uid,
            "email":   result["email"],
            "gym_id":  gym_id,
            "message": "Usuario registrado exitosamente"
        }, status=status.HTTP_201_CREATED)


# =========================================
# LOGIN (API) - CORRECCIÓN ARQUITECTÓNICA COMPLETA
# =========================================
@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    email    = request.data.get('email')
    password = request.data.get('password')

    if not email or not password:
        return Response(
            {"error": "Email y password son requeridos"},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Autenticación e identificación de rol contra Firebase unificada
    result = login_user(email, password)

    if "error" in result:
        return Response(
            {"error": "Credenciales inválidas"},
            status=status.HTTP_401_UNAUTHORIZED
        )

    try:
        # Sincronización con el modelo de Django para la sesión local
        user, created = User.objects.get_or_create(
            username=email,
            defaults={'email': email}
        )

        # Persistencia clave en la sesión del servidor (Para tags {% if %})
        request.session['user_uid'] = result["uid"]
        request.session['user_rol'] = result.get("rol", "atleta")

        # También guardamos gym_id en sesión si viene del perfil
        gym_id = result.get("gym_id")
        if gym_id:
            request.session['gym_id'] = gym_id

        login(request, user)

        # Retorno completo de llaves hacia el LocalStorage de JS
        return Response({
            "token":  result.get("idToken"),
            "uid":    result["uid"],
            "email":  email,
            "rol":    result.get("rol", "atleta"),
            "gym_id": gym_id,
            "message": "Login exitoso"
        }, status=status.HTTP_200_OK)

    except Exception as e:
        print(f"[BIO-FIT Error] Error en login_view: {e}")
        return Response(
            {"error": "Error interno al procesar la sesión"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )