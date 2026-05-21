import logging
from django.shortcuts import render, redirect
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from services.firebase_client import FirebaseClient

logger = logging.getLogger(__name__)
firebase = FirebaseClient()

def get_session_tenant(request):
    """Valida la sesión del administrador y extrae de forma segura su gym_id asignado."""
    uid = request.session.get('user_uid')
    rol = request.session.get('user_rol')
    gym_id = request.session.get('gym_id')
    
    # Si tiene sesión iniciada pero no tiene el gym_id en las cookies, lo rescatamos de su perfil en Firestore
    if uid and rol == 'admin' and not gym_id:
        perfil = firebase.get_user_profile(uid)
        if perfil and 'gym_id' in perfil:
            request.session['gym_id'] = perfil['gym_id']
            request.session.modified = True
            gym_id = perfil['gym_id']

    if not uid or rol != 'admin' or not gym_id:
        return None
    return gym_id


# ── VISTAS RENDERIZADAS (HTML) ──────────────────────────────────────────────

def admin_dashboard_view(request):
    gym_id = get_session_tenant(request)
    if not gym_id:
        # Si el administrador no tiene una sede registrada aún, lo redirigimos al formulario
        if request.session.get('user_rol') == 'admin':
            return redirect('inventory:registrar_gimnasio_view')
        return redirect('login')
    
    # Consulta los equipos directo desde la subcolección interna del gimnasio activo
    inventario = firebase.get_all_equipment(gym_id)
    return render(request, 'inventory/dashboard.html', {
        'inventario': inventario,
        'gym_id': gym_id
    })


def registrar_gimnasio_page(request):
    """Renderiza el formulario administrativo de creación de gimnasios."""
    if request.session.get('user_rol') != 'admin':
        return redirect('landing')
    return render(request, 'inventory/registrar_gimnasio.html')


# ── ENDPOINTS DE OPERACIONES (API) ──────────────────────────────────────────

class GimnasioCreateAPI(APIView):
    """API funcional para la creación e inicialización de Gimnasios."""
    def post(self, request):
        if request.session.get('user_rol') != 'admin':
            return Response({"error": "No autorizado."}, status=status.HTTP_403_FORBIDDEN)
            
        uid = request.session.get('user_uid')
        nombre = request.data.get('nombre')
        ubicacion = request.data.get('ubicacion')
        telefono = request.data.get('telefono')

        if not nombre or not ubicacion:
            return Response({"error": "Nombre y Ubicación son requeridos"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            payload = {
                'nombre': nombre,
                'ubicacion': ubicacion,
                'telefono': telefono or 'No especificado',
                'creado_por': uid
            }
            # 1. Creamos el gimnasio en la colección principal raíz
            gym_id = firebase.create_gym(payload)
            
            # 2. Vinculación inmediata en cookies de sesión del navegador
            request.session['gym_id'] = gym_id
            request.session.modified = True
            
            # 3. Vinculación persistente en el documento de perfil del administrador en Firestore
            if uid:
                firebase.save_user_profile(uid, {'gym_id': gym_id})

            return Response({
                "success": True, 
                "gym_id": gym_id,
                "message": "Gimnasio creado y sincronizado con éxito."
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class EquiposListCreateAPI(APIView):
    def post(self, request):
        gym_id = get_session_tenant(request)
        if not gym_id:
            return Response({"error": "No autorizado o gimnasio no inicializado en sesión."}, status=status.HTTP_403_FORBIDDEN)

        data = request.data
        nombre = data.get('nombre')
        tipo = data.get('tipo')
        estado = data.get('estado')
        fecha = data.get('fecha_adquisicion')
        ubicacion = data.get('ubicacion')

        if not all([nombre, tipo, estado, fecha, ubicacion]):
            return Response({"error": "Todos los campos son obligatorios"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            nuevo_equipo = {
                'nombre': nombre,
                'tipo': tipo,
                'estado': estado,
                'fecha_adquisicion': fecha,
                'ubicacion': ubicacion
            }
            # Guarda de forma limpia en la subcolección interna /gimnasios/{gym_id}/equipamientos/
            equipo_id = firebase.create_equipment(gym_id, nuevo_equipo)
            return Response({"success": True, "id": equipo_id}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class EquipoDetailAPI(APIView):
    def put(self, request, equipo_id):
        gym_id = get_session_tenant(request)
        if not gym_id:
            return Response({"error": "No autorizado"}, status=status.HTTP_403_FORBIDDEN)

        try:
            data = request.data
            firebase.update_equipment(gym_id, equipo_id, {
                'nombre': data.get('nombre'),
                'tipo': data.get('tipo'),
                'estado': data.get('estado'),
                'fecha_adquisicion': data.get('fecha_adquisicion'),
                'ubicacion': data.get('ubicacion')
            })
            return Response({"success": True})
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class EquipoDeleteAPI(APIView):
    def delete(self, request, equipo_id):
        gym_id = get_session_tenant(request)
        if not gym_id:
            return Response({"error": "No autorizado"}, status=status.HTTP_403_FORBIDDEN)

        try:
            firebase.delete_equipment(gym_id, equipo_id)
            return Response({"success": True})
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)