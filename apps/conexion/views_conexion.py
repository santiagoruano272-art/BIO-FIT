from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.models import User
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from apps.conexion.auth import login_user, confirmar_cambio_password, ROL_MAP


# =========================================
# VISTAS DE PLANTILLAS HTML
# =========================================

def landing_page(request):
    return render(request, 'landing.html')


def login_page(request):
    return render(request, 'users/login.html')


def cambiar_password_page(request):
    """
    Vista que se muestra cuando el admin inicia sesión por primera vez
    con contraseña provisional. Solo accesible si hay un uid bloqueado
    en sesión.
    """
    if not request.session.get('uid_pending_password_change'):
        return redirect('login')
    return render(request, 'users/cambiar_password.html')


# =========================================
# LOGIN (API)
# =========================================

@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    email    = request.data.get('email', '').strip()
    password = request.data.get('password', '')

    if not email or not password:
        return Response(
            {"error": "Email y contraseña son requeridos."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    result = login_user(email, password)

    # ── BLOQUEO: contraseña provisional detectada ──────────────────────────
    # login_user detectó must_change_password=True en el perfil.
    # Guardamos el uid en sesión para que cambiar_password_page lo use.
    if result.get("must_change_password"):
        request.session['uid_pending_password_change']   = result.get("uid")
        request.session['email_pending_password_change'] = email
        return Response(
            {
                "must_change_password": True,
                "redirect":             "/cambiar-password/",
                "error":                result["error"],
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    if "error" in result:
        return Response(
            {"error": "Credenciales inválidas."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    try:
        # Sincronización con sesión Django
        user, _ = User.objects.get_or_create(
            username=email,
            defaults={'email': email},
        )

        # Normalizar rol legacy ('gym_owner' → 'admin') por si el perfil
        # en Firestore aún no fue migrado con migrar_rol_gym_owner()
        rol_raw = result.get("rol", "admin")
        rol     = ROL_MAP.get(rol_raw, rol_raw)

        request.session['user_uid'] = result["uid"]
        request.session['user_rol'] = rol
        request.session['gym_id']   = result.get("gym_id")

        login(request, user)

        return Response(
            {
                "token":    result.get("idToken"),
                "uid":      result["uid"],
                "email":    email,
                "rol":      rol,
                "gym_id":   result.get("gym_id"),
                "redirect": "/inventory/dashboard/",
                "message":  "Login exitoso",
            },
            status=status.HTTP_200_OK,
        )

    except Exception as e:
        print(f"[BIO-FIT Error] Error en login_view: {e}")
        return Response(
            {"error": "Error interno al procesar la sesión."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# =========================================
# CONFIRMAR CAMBIO DE CONTRASEÑA (API)
# =========================================

@api_view(['POST'])
@permission_classes([AllowAny])
def confirmar_password_view(request):
    """
    El admin llama a este endpoint después de cambiar su contraseña
    desde el email de Firebase. Elimina el bloqueo y redirige al dashboard.
    """
    uid = request.session.get('uid_pending_password_change')

    if not uid:
        return Response(
            {"error": "No hay una sesión de cambio de contraseña activa."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    ok = confirmar_cambio_password(uid)

    if not ok:
        return Response(
            {"error": "No se pudo actualizar el estado de la contraseña."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    # Limpiar claves temporales de sesión
    request.session.pop('uid_pending_password_change', None)
    request.session.pop('email_pending_password_change', None)

    return Response(
        {
            "success":  True,
            "redirect": "/inventory/dashboard/",
            "message":  "Contraseña actualizada. Ya puedes acceder al panel.",
        },
        status=status.HTTP_200_OK,
    )