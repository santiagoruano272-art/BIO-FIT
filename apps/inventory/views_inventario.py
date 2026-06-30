import logging
from django.shortcuts import render, redirect
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status
from services.firebase_client import FirebaseClient

logger   = logging.getLogger(__name__)
firebase = FirebaseClient()

# Roles válidos para acceso de administrador.
# Incluye 'gym_owner' durante la transición hasta que todos los perfiles
# en Firestore sean migrados con migrar_rol_gym_owner().
ROLES_ADMIN = {'admin', 'gym_owner'}


# ── HELPERS ──────────────────────────────────────────────────────────────────

def is_admin(request) -> bool:
    """Retorna True si el usuario en sesión tiene un rol de administrador."""
    return request.session.get('user_rol') in ROLES_ADMIN


def get_admin_tenant(request):
    """
    Valida que la sesión pertenezca a un admin con gym_id asignado.
    Si gym_id no está en sesión, lo recupera desde Firestore.
    Retorna gym_id (str) o None si la sesión no es válida.
    """
    uid    = request.session.get('user_uid')
    rol    = request.session.get('user_rol')
    gym_id = request.session.get('gym_id')

    if not uid or rol not in ROLES_ADMIN:
        return None

    if not gym_id:
        try:
            perfil = firebase.get_user_profile(uid)
            if perfil and perfil.get('gym_id'):
                gym_id = perfil['gym_id']
                request.session['gym_id'] = gym_id
                request.session.modified  = True
        except Exception as e:
            logger.error("Error recuperando gym_id desde Firestore: %s", e)

    return gym_id or None


def get_gym_context(request, gym_id: str) -> dict:
    """
    Construye el contexto completo del gimnasio para el template:
    nombre, logo, dirección, conteo de máquinas y atletas.
    Cachea el nombre en sesión para evitar llamadas repetidas.
    """
    context = {
        'gym_nombre':    'Gimnasio',
        'gym_logo':      None,
        'gym_direccion': '',
        'gym_email':     '',
        'total_equipos': 0,
        'total_atletas': 0,
    }

    # ── Datos del gimnasio ────────────────────────────────────────────────
    try:
        gyms = firebase.get_all_gyms()
        gym  = next((g for g in gyms if g.get('id') == gym_id), None)
        if gym:
            gym_nombre = gym.get('nombre', 'Gimnasio')
            context['gym_nombre']    = gym_nombre
            context['gym_logo']      = gym.get('logo_url')
            context['gym_direccion'] = gym.get('ubicacion') or gym.get('direccion', '')
            context['gym_email']     = gym.get('email', '')
            request.session['gym_nombre'] = gym_nombre
            request.session.modified      = True
    except Exception as e:
        logger.error("Error obteniendo datos del gimnasio: %s", e)
        context['gym_nombre'] = request.session.get('gym_nombre', 'Gimnasio')

    # ── Conteo de máquinas ────────────────────────────────────────────────
    try:
        equipos = firebase.get_all_equipment(gym_id)
        context['total_equipos'] = len(equipos) if equipos else 0
    except Exception as e:
        logger.error("Error contando equipos: %s", e)

    # ── Conteo de atletas vinculados al gimnasio ──────────────────────────
    try:
        atletas = (
            firebase.db.collection('usuarios')
            .where('gym_id', '==', gym_id)
            .where('rol', '==', 'atleta')
            .stream()
        )
        context['total_atletas'] = sum(1 for _ in atletas)
    except Exception as e:
        logger.error("Error contando atletas: %s", e)

    return context


# ── VISTAS HTML ──────────────────────────────────────────────────────────────

def dashboard_view(request):
    """
    Vista principal del inventario. Solo accesible para admin.
    Muestra datos del gimnasio, conteo de máquinas y atletas.
    """
    gym_id = get_admin_tenant(request)
    if not gym_id:
        return redirect('login')

    gym_context = get_gym_context(request, gym_id)
    inventario  = firebase.get_all_equipment(gym_id)

    return render(request, 'inventory/dashboard.html', {
        **gym_context,
        'inventario': inventario,
        'gym_id':     gym_id,
        'es_admin':   True,
    })


# ── ENDPOINTS API ─────────────────────────────────────────────────────────────

class EquiposListCreateAPI(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        gym_id = get_admin_tenant(request)
        if not gym_id:
            return Response({"error": "No autorizado."}, status=status.HTTP_403_FORBIDDEN)
        try:
            equipos = firebase.get_all_equipment(gym_id)
            return Response({"equipos": equipos}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        gym_id = get_admin_tenant(request)
        if not gym_id:
            return Response(
                {"error": "Acceso denegado. Solo administradores pueden agregar equipos.", "code": "ADMIN_REQUIRED"},
                status=status.HTTP_403_FORBIDDEN,
            )
        data      = request.data
        nombre    = data.get('nombre')
        tipo      = data.get('tipo')
        estado    = data.get('estado')
        fecha     = data.get('fecha_adquisicion')
        ubicacion = data.get('ubicacion')

        if not all([nombre, tipo, estado, fecha, ubicacion]):
            return Response({"error": "Todos los campos son obligatorios."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            equipo_id = firebase.create_equipment(gym_id, {
                'nombre': nombre, 'tipo': tipo, 'estado': estado,
                'fecha_adquisicion': fecha, 'ubicacion': ubicacion,
            })
            return Response({"success": True, "id": equipo_id}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class EquipoDetailAPI(APIView):
    permission_classes = [AllowAny]

    def put(self, request, equipo_id):
        gym_id = get_admin_tenant(request)
        if not gym_id:
            return Response(
                {"error": "Acceso denegado. Solo administradores pueden editar equipos.", "code": "ADMIN_REQUIRED"},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            data = request.data
            firebase.update_equipment(gym_id, equipo_id, {
                'nombre': data.get('nombre'), 'tipo': data.get('tipo'),
                'estado': data.get('estado'), 'fecha_adquisicion': data.get('fecha_adquisicion'),
                'ubicacion': data.get('ubicacion'),
            })
            return Response({"success": True})
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class EquipoDeleteAPI(APIView):
    permission_classes = [AllowAny]

    def delete(self, request, equipo_id):
        gym_id = get_admin_tenant(request)
        if not gym_id:
            return Response(
                {"error": "Acceso denegado. Solo administradores pueden eliminar equipos.", "code": "ADMIN_REQUIRED"},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            firebase.delete_equipment(gym_id, equipo_id)
            return Response({"success": True})
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GimnasiosPublicListAPI(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            gyms_raw  = firebase.get_all_gyms()
            gimnasios = [
                {"id": g.get("id") or g.get("gym_id"), "nombre": g.get("nombre", "Sin nombre"), "ubicacion": g.get("ubicacion", "")}
                for g in (gyms_raw or [])
            ]
            return Response({"gimnasios": gimnasios}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error("Error listando gimnasios públicos: %s", e)
            return Response({"gimnasios": []}, status=status.HTTP_200_OK)


class GimnasioContextoAPI(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        gym_id = request.session.get('gym_id')
        if not gym_id:
            return Response({"gym_id": None, "gym_nombre": None})
        try:
            gyms   = firebase.get_all_gyms()
            gym    = next((g for g in gyms if g.get('id') == gym_id), None)
            nombre = gym.get('nombre', 'Gimnasio') if gym else 'Gimnasio'
            return Response({"gym_id": gym_id, "gym_nombre": nombre})
        except Exception as e:
            logger.error("Error en contexto de gimnasio: %s", e)
            return Response({"gym_id": None, "gym_nombre": None})