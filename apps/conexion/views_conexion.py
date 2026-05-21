from django.shortcuts import render, redirect
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

# =========================================================================
# VISTAS DE PLANTILLAS HTML
# =========================================================================
def landing_page(request):
    # Recuperamos el rol de la sesión de Django
    user_rol = request.session.get('user_rol', 'atleta')
    
    # Pasamos explícitamente el rol al contexto para que el HTML lo procese
    return render(request, 'landing.html', {'user_rol': user_rol})

def login_page(request):
    return render(request, 'users/login.html')

def registro_page(request):
    return render(request, 'users/registro.html')


# =========================================================================
# REGISTRO (API)
# =========================================================================
class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")
        requested_role = request.data.get("rol", "atleta")

        if not email or not password:
            return Response(
                {"error": "Email y password son requeridos"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if requested_role not in ['atleta', 'admin', 'entrenador']:
            return Response({"error": "El rol especificado no es válido."}, status=status.HTTP_400_BAD_REQUEST)

        # Seguridad: Bloquear creación anónima de administradores
        if requested_role == 'admin':
            current_user_uid = request.session.get('user_uid')
            is_authorized = False
            if current_user_uid:
                perfil = firebase.get_user_profile(current_user_uid) or {}
                if perfil.get('rol') == 'admin':
                    is_authorized = True
            
            if not is_authorized:
                return Response(
                    {"error": "No tienes permisos para crear cuentas de administrador."},
                    status=status.HTTP_403_FORBIDDEN
                )

        result = register_user(email, password, requested_role)
        
        if "error" in result:
            return Response({"error": result["error"]}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "uid": result["uid"],
            "email": result["email"],
            "rol": result["rol"],
            "message": "Usuario registrado exitosamente."
        }, status=status.HTTP_201_CREATED)


# =========================================================================
# LOGIN (API) — CORREGIDO PARA EXTRAER Y PERSISTIR ROL
# =========================================================================
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

    # Autenticación en Firebase Auth
    result = login_user(email, password)

    if "error" in result:
        return Response(
            {"error": "Credenciales inválidas"}, 
            status=status.HTTP_401_UNAUTHORIZED
        )

    try:
        uid = result["uid"]
        
        # 1. Consultar el rol real del usuario en Firestore
        perfil = firebase.get_user_profile(uid) or {}
        user_rol = perfil.get('rol', 'atleta') 

        # 2. Sincronizar con la base de datos interna de Django
        user, created = User.objects.get_or_create(
            username=email, 
            defaults={'email': email}
        )
        
        if user_rol == 'admin':
            user.is_staff = True
            user.save()
        else:
            if user.is_staff:
                user.is_staff = False
                user.save()
        
        # 3. Guardar variables de estado en la sesión de Django (Cookies)
        request.session['user_uid'] = uid
        request.session['user_rol'] = user_rol  
        request.session.modified = True # Forzar a Django a guardar la cookie inmediatamente
        
        login(request, user)

        # 4. Retornar respuesta incluyendo el rol para el LocalStorage del cliente
        return Response({
            "token": result.get("idToken"),
            "uid": uid,
            "email": email,
            "rol": user_rol,
            "message": "Login exitoso"
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response(
            {"error": f"Error interno en el servidor: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )