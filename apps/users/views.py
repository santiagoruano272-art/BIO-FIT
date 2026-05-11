from django.shortcuts import render
from django.contrib.auth import login
from django.contrib.auth.models import User
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from apps.conexion.auth import register_user, login_user

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

    def get(self, request):
        return Response({"msg": "Endpoint REGISTER activo. Usa POST"})

    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")

        if not email or not password:
            return Response(
                {"error": "Email y password son requeridos"},
                status=status.HTTP_400_BAD_REQUEST
            )

        result = register_user(email, password)

        if "error" in result:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "message": "Usuario creado correctamente",
            "uid": result["uid"],
            "email": result["email"]
        })

# =========================================
# LOGIN (API) CORREGIDO PARA SESIÓN DJANGO
# =========================================
@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def login_view(request):
    if request.method == "GET":
        return Response({"msg": "Endpoint LOGIN activo. Usa POST"})

    email = request.data.get('email')
    password = request.data.get('password')

    if not email or not password:
        return Response(
            {"error": "Email y password son requeridos"},
            status=status.HTTP_400_BAD_REQUEST
        )

    result = login_user(email, password)

    if "error" in result:
        return Response(result, status=status.HTTP_400_BAD_REQUEST)

    # --- SINCRONIZACIÓN CON DJANGO ---
    user, created = User.objects.get_or_create(
        username=email, 
        defaults={'email': email}
    )
    login(request, user)
    # --------------------------------

    return Response({
        "message": "Login exitoso",
        "token": result["idToken"],
        "uid": result["uid"]
    })
