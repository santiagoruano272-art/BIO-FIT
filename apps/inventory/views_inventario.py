import logging
import functools
from django.shortcuts import render, redirect
from django.contrib import messages
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from services.firebase_client import FirebaseClient
from .serializers_inventario import EquipmentSerializer

logger = logging.getLogger(__name__)
firebase = FirebaseClient()

# ── DECORADOR DE PROTECCIÓN PARA VISTAS RENDERIZADAS ──────────────────────
def admin_required(view_func):
    """
    Verifica que el usuario esté logueado en la sesión de Django
    y que su rol en Firestore sea 'admin'.

    FIX: Se añadió @functools.wraps(view_func) para preservar el nombre
    y los metadatos de la vista original, necesario para que Django
    pueda introspectarla correctamente (ej. en el decorador @login_required,
    en la barra de debug, y en reverse() con name=).
    """
    @functools.wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        uid = request.session.get('user_uid')
        if not uid:
            messages.error(request, "Debes iniciar sesión para acceder.")
            return redirect('conexion:login_page')

        # Validar rol en Firebase
        try:
            perfil = firebase.get_user_profile(uid) or {}
        except Exception as e:
            logger.error(f"[ADMIN_REQUIRED] Error al obtener perfil de Firebase: {e}")
            messages.error(request, "Error al verificar tus permisos. Intenta de nuevo.")
            return redirect('conexion:login_page')

        rol = perfil.get('rol')

        # Fallback: si el campo no existe, tratar como usuario sin privilegios
        if not rol:
            logger.warning(f"[ADMIN_REQUIRED] UID {uid} no tiene campo 'rol' en Firestore.")
            messages.error(request, "Tu cuenta no tiene un rol asignado. Contacta al administrador.")
            return redirect('landing_page')

        if rol != 'admin':
            messages.error(request, "Acceso denegado. Se requieren permisos de administrador.")
            return redirect('landing_page')

        return view_func(request, *args, **kwargs)
    return _wrapped_view


# ── VISTA PRINCIPAL (TEMPLATE) ────────────────────────────────────────────
@admin_required
def inventory_dashboard_view(request):
    """Muestra la tabla de inventario y los formularios de gestión."""
    try:
        docs = firebase.db.collection('equipamientos').stream()
        inventario = []
        for doc in docs:
            data = doc.to_dict()
            data['id'] = doc.id
            inventario.append(data)
    except Exception as e:
        logger.error(f"[INVENTARIO] Error al cargar Firestore: {e}")
        inventario = []
        messages.error(request, "Error al conectar con la base de datos de inventario.")

    return render(request, 'inventory/dashboard.html', {'inventario': inventario})


# ── ENDPOINTS API PARA CONTROL CRUD (DRF) ────────────────────────────────

def _get_admin_uid(request):
    """
    Helper interno: devuelve el UID si el usuario autenticado es admin,
    o None en caso contrario. Centraliza la lógica de autorización API.
    """
    uid = request.session.get('user_uid')
    if not uid:
        return None
    try:
        perfil = firebase.get_user_profile(uid) or {}
    except Exception:
        return None
    return uid if perfil.get('rol') == 'admin' else None


@api_view(['POST'])
@permission_classes([AllowAny])
def create_equipment_api(request):
    """Crea una nueva máquina en Firestore."""
    if not _get_admin_uid(request):
        return Response({"error": "No autorizado"}, status=status.HTTP_403_FORBIDDEN)

    serializer = EquipmentSerializer(data=request.data)

    # FIX: era serializer.is_validated() — método inexistente en DRF.
    # El correcto es serializer.is_valid(), que ejecuta la validación
    # y popula serializer.errors / serializer.validated_data.
    if serializer.is_valid():
        try:
            ref_doc = firebase.db.collection('equipamientos').document()
            data = serializer.validated_data
            data['fecha_adquisicion'] = data['fecha_adquisicion'].isoformat()
            ref_doc.set(data)
            return Response(
                {"success": True, "id": ref_doc.id, "message": "Equipo registrado con éxito."},
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            logger.error(f"[INVENTARIO] Error al crear equipo: {e}")
            return Response(
                {"error": f"Error de servidor: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT'])
@permission_classes([AllowAny])
def update_equipment_api(request, equip_id):
    """Actualiza una máquina existente."""
    if not _get_admin_uid(request):
        return Response({"error": "No autorizado"}, status=status.HTTP_403_FORBIDDEN)

    doc_ref = firebase.db.collection('equipamientos').document(equip_id)
    if not doc_ref.get().exists:
        return Response({"error": "El equipo no existe."}, status=status.HTTP_404_NOT_FOUND)

    serializer = EquipmentSerializer(data=request.data)
    if serializer.is_valid():
        try:
            data = serializer.validated_data
            data['fecha_adquisicion'] = data['fecha_adquisicion'].isoformat()
            doc_ref.update(data)
            return Response({"success": True, "message": "Equipo actualizado correctamente."})
        except Exception as e:
            logger.error(f"[INVENTARIO] Error al actualizar equipo {equip_id}: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([AllowAny])
def delete_equipment_api(request, equip_id):
    """Elimina una máquina del inventario de forma definitiva."""
    if not _get_admin_uid(request):
        return Response({"error": "No autorizado"}, status=status.HTTP_403_FORBIDDEN)

    try:
        doc_ref = firebase.db.collection('equipamientos').document(equip_id)
        if not doc_ref.get().exists:
            return Response({"error": "El elemento ya no existe."}, status=status.HTTP_404_NOT_FOUND)

        doc_ref.delete()
        return Response({"success": True, "message": "Máquina eliminada del sistema."})
    except Exception as e:
        logger.error(f"[INVENTARIO] Error al eliminar equipo {equip_id}: {e}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)