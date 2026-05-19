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
# REGISTRO (API) - SIN CAMPO NOMBRE
# =========================================
class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")

        if not email or not password:
            return Response(
                {"error": "Email y password son requeridos"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Registro en Firebase sin enviar el parámetro nombre
        result = register_user(email, password)
        
        if "error" in result:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Sincronización local en Django
            user, created = User.objects.get_or_create(
                username=email, 
                defaults={'email': email}
            )

            # Guardamos el UID de Firebase en la sesión de Django
            request.session['user_uid'] = result["uid"]
            login(request, user)

            return Response({
                "message": "Usuario creado correctamente",
                "uid": result["uid"],
                "email": result["email"]
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(
                {"error": f"Error en base de datos local: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

# =========================================
# LOGIN (API) - CORRECCIÓN DE LA TUPLA
# =========================================
@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    email = request.data.get('email')
    password = request.data.get('password')

    if not email or not password:
        return Response(
            {"error": "Email y password son requeridos"},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Autenticación contra Firebase REST API
    result = login_user(email, password)

    if "error" in result:
        return Response(
            {"error": "Credenciales inválidas"}, 
            status=status.HTTP_401_UNAUTHORIZED
        )

    try:
        # Sincronización con Django para mantener la sesión HTTP activa
        user, created = User.objects.get_or_create(
            username=email, 
            defaults={'email': email}
        )
        
        # AQUÍ ESTABA EL ERROR: Aseguramos la lectura correcta del diccionario 'result'
        request.session['user_uid'] = result["uid"]
        login(request, user)

        return Response({
            "token": result.get("idToken"),
            "uid": result["uid"],
            "email": email,
            "message": "Login exitoso"
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response(
            {"error": f"Error al sincronizar sesión local: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )