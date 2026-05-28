from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.models import User
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from apps.conexion.auth import register_user, login_user
from apps.conexion.serializers_conexion import RegisterSerializer
from services.firebase_client import FirebaseClient

firebase = FirebaseClient()

def landing_page(request):
    user_rol = request.session.get('user_rol', 'atleta')
    return render(request, 'landing.html', {'user_rol': user_rol})

def login_page(request):
    if request.session.get('user_rol') == 'admin':
        return redirect('inventory:admin_dashboard')
    return render(request, 'users/login.html')

def registro_page(request):
    # Catálogo simulado de sedes disponibles para el registro
    gimnasios_disponibles = [
        {'id': 'gym_bogota_norte', 'nombre': 'BIO-FIT Sede Bogotá Norte'},
        {'id': 'gym_medellin_poblado', 'nombre': 'BIO-FIT Sede Medellín Poblado'},
        {'id': 'gym_cali_sur', 'nombre': 'BIO-FIT Sede Cali Sur'},
    ]
    return render(request, 'users/registro.html', {'gimnasios': gimnasios_disponibles})


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data.get("email")
        password = serializer.validated_data.get("password")
        requested_role = serializer.validated_data.get("rol", "atleta")
        gym_id = serializer.validated_data.get("gym_id", None)

        result = register_user(email, password, requested_role, gym_id)
        
        if "error" in result:
            return Response({"error": result["error"]}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "uid": result["uid"],
            "email": result["email"],
            "rol": result["rol"],
            "gym_id": result.get("gym_id"),
            "message": "Usuario registrado con éxito."
        }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    email = request.data.get('email')
    password = request.data.get('password')

    if not email or not password:
        return Response({"error": "Email y password son requeridos"}, status=status.HTTP_400_BAD_REQUEST)

    result = login_user(email, password)

    if "error" in result:
        return Response({"error": "Credenciales inválidas en el sistema"}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        uid = result["uid"]
        user_rol = result["rol"]
        gym_id = result["gym_id"]

        user, created = User.objects.get_or_create(
            username=email, 
            defaults={'email': email}
        )
        
        user.is_staff = (user_rol == 'admin')
        user.save()
        
        # Guardar en sesión de Django de forma persistente
        request.session['user_uid'] = uid
        request.session['user_rol'] = user_rol  
        request.session['gym_id'] = gym_id  
        request.session.modified = True 
        
        login(request, user)

        return Response({
            "token": result.get("idToken"),
            "uid": uid,
            "email": email,
            "rol": user_rol,
            "gym_id": gym_id,
            "redirect_url": "/inventory/dashboard/" if user_rol == 'admin' else "/routines/generar/",
            "message": "Autenticación exitosa."
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response(
            {"error": f"Falla interna: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    # original