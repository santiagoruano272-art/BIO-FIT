"""
views_perfil.py  –  BIO-FIT
Versión corregida: unifica el identificador de gimnasio usando
firebase.get_all_gyms() + búsqueda por campo 'gym_id', igual que
GimnasiosPublicListAPI en views_inventario.py.

Problema resuelto:
  Cada documento en /gimnasios/ tiene DOS identificadores:
    • doc.id  → ID autogenerado por Firestore
    • gym_id  → campo interno guardado en el documento Y en el perfil del usuario
  La versión anterior mezclaba ambos, provocando que la verificación de
  existencia fallara y se mostrara el fallback con gimnasios inventados.
"""

import logging
from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny

from apps.conexion.firebase_auth import FirebaseAuthentication
from services.firebase_client import FirebaseClient

logger = logging.getLogger(__name__)
firebase = FirebaseClient()


# ─────────────────────────────────────────────────────────────────
# UTILIDAD INTERNA: buscar un gimnasio por su campo gym_id
# Usa get_all_gyms() para ser consistente con el resto de la app.
# ─────────────────────────────────────────────────────────────────
def _buscar_gym_por_id(gym_id: str) -> dict | None:
    """
    Devuelve el dict del gimnasio cuyo campo 'gym_id' (o 'id') coincida,
    o None si no se encuentra.
    Funciona aunque doc.id y gym_id sean valores distintos.
    """
    try:
        gyms = firebase.get_all_gyms() or []
        for g in gyms:
            # get_all_gyms puede devolver 'id' (doc.id mapeado) o 'gym_id'
            if g.get('gym_id') == gym_id or g.get('id') == gym_id:
                return g
    except Exception as e:
        logger.error("Error en _buscar_gym_por_id: %s", e)
    return None


# ─────────────────────────────────────────────────────────────────
# PÁGINA HTML  →  GET /perfil/
# ─────────────────────────────────────────────────────────────────
def perfil_page(request):
    """Renderiza la plantilla del perfil de usuario."""
    return render(request, 'users/perfil.html')


# ─────────────────────────────────────────────────────────────────
# API: LEER Y ACTUALIZAR PERFIL  →  /api/perfil/
# ─────────────────────────────────────────────────────────────────
class PerfilView(APIView):
    authentication_classes = [FirebaseAuthentication]

    def get(self, request):
        """Devuelve el perfil completo del usuario autenticado."""
        uid = request.user.uid
        try:
            perfil = firebase.get_user_profile(uid) or {}
            gym_id     = perfil.get('gym_id')
            gym_nombre = None
            gym_ubicacion = None

            # Buscar nombre del gimnasio usando la misma lógica que el resto de la app
            if gym_id:
                gym = _buscar_gym_por_id(gym_id)
                if gym:
                    gym_nombre    = gym.get('nombre', gym_id)
                    gym_ubicacion = gym.get('ubicacion', '')
                else:
                    # gym_id guardado en el usuario ya no existe en Firestore
                    gym_nombre = f"Gimnasio no encontrado ({gym_id})"
                    logger.warning("gym_id '%s' del usuario %s no existe en Firestore", gym_id, uid)

            return Response({
                'nombre':       perfil.get('nombre', ''),
                'email':        perfil.get('email', ''),
                'telefono':     perfil.get('telefono', ''),
                'nivel':        perfil.get('nivel', 'principiante'),
                'rol':          perfil.get('rol', 'atleta'),
                'gym_id':       gym_id,
                'gym_nombre':   gym_nombre,
                'gym_ubicacion': gym_ubicacion,
            })

        except Exception as e:
            logger.error("Error en PerfilView.get para uid %s: %s", uid, e)
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request):
        """Actualiza nombre, email y/o teléfono del perfil."""
        import re
        uid = request.user.uid
        datos_permitidos = {}

        nombre   = request.data.get('nombre', '').strip()
        email    = request.data.get('email', '').strip()
        telefono = request.data.get('telefono', '').strip()

        if nombre:
            datos_permitidos['nombre'] = nombre
        if email:
            if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
                return Response(
                    {'error': 'Correo electrónico no válido.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            datos_permitidos['email'] = email
        if telefono:
            datos_permitidos['telefono'] = telefono

        if not datos_permitidos:
            return Response(
                {'error': 'No se proporcionaron datos para actualizar.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # ✅ Colección correcta: 'usuarios' (no 'users')
            firebase.db.collection('usuarios').document(uid).set(datos_permitidos, merge=True)
            return Response({'message': 'Perfil actualizado correctamente.', **datos_permitidos})
        except Exception as e:
            logger.error("Error actualizando perfil de %s: %s", uid, e)
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ─────────────────────────────────────────────────────────────────
# API: VINCULAR / DESVINCULAR GIMNASIO  →  /api/perfil/gimnasio/
# ─────────────────────────────────────────────────────────────────
class GimnasioVinculacionView(APIView):
    authentication_classes = [FirebaseAuthentication]

    def post(self, request):
        """Vincula el usuario al gimnasio indicado en {gym_id}."""
        uid    = request.user.uid
        gym_id = request.data.get('gym_id', '').strip()

        if not gym_id:
            return Response(
                {'error': 'gym_id es requerido.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ✅ Verificar existencia usando _buscar_gym_por_id (no por doc.id)
        gym = _buscar_gym_por_id(gym_id)
        if not gym:
            return Response(
                {'error': 'El gimnasio seleccionado no existe o fue eliminado.'},
                status=status.HTTP_404_NOT_FOUND
            )

        gym_nombre    = gym.get('nombre', gym_id)
        gym_ubicacion = gym.get('ubicacion', '')

        try:
            # ✅ Colección correcta: 'usuarios'
            firebase.db.collection('usuarios').document(uid).set(
                {'gym_id': gym_id}, merge=True
            )
            return Response({
                'message':       f'Vinculado a "{gym_nombre}" exitosamente.',
                'gym_id':        gym_id,
                'gym_nombre':    gym_nombre,
                'gym_ubicacion': gym_ubicacion,
            })
        except Exception as e:
            logger.error("Error vinculando gym para %s: %s", uid, e)
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request):
        """Desvincula el usuario de su gimnasio actual."""
        uid = request.user.uid
        try:
            from google.cloud.firestore_v1 import DELETE_FIELD
            # ✅ Colección correcta: 'usuarios'
            firebase.db.collection('usuarios').document(uid).update(
                {'gym_id': DELETE_FIELD}
            )
            return Response({'message': 'Desvinculado del gimnasio correctamente.'})
        except Exception as e:
            logger.error("Error desvinculando gym para %s: %s", uid, e)
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ─────────────────────────────────────────────────────────────────
# API: BUSCAR GIMNASIOS  →  /api/gimnasios/?q=<query>
# ─────────────────────────────────────────────────────────────────
class GimnasioBuscadorView(APIView):
    """
    Devuelve los gimnasios reales de Firestore.
    Usa firebase.get_all_gyms() para ser 100% consistente con
    GimnasiosPublicListAPI en views_inventario.py.

    Filtro opcional: ?q=<nombre o ubicacion>
    Campo de búsqueda: 'ubicacion' (NO 'ciudad', que no existe en Firestore).
    """
    authentication_classes = [FirebaseAuthentication]

    def get(self, request):
        q = request.query_params.get('q', '').strip().lower()

        try:
            gyms_raw = firebase.get_all_gyms() or []

            if not gyms_raw:
                # Firestore devolvió lista vacía (no es un error, simplemente no hay sedes)
                return Response([])

            sedes = []
            for g in gyms_raw:
                # ✅ Usar el identificador que usa el resto de la app
                gym_id    = g.get('gym_id') or g.get('id')
                nombre    = g.get('nombre', '')
                ubicacion = g.get('ubicacion', '')   # ✅ 'ubicacion', no 'ciudad'

                if not gym_id:
                    continue  # documento malformado, ignorar

                # Filtrar por texto si se proporcionó ?q=
                if q and q not in nombre.lower() and q not in ubicacion.lower():
                    continue

                sedes.append({
                    'id':       gym_id,
                    'nombre':   nombre,
                    'ubicacion': ubicacion,   # ✅ clave corregida
                })

            return Response(sedes)

        except Exception as e:
            # ✅ Sin fallback de datos inventados — devolver error claro
            logger.error("Error en GimnasioBuscadorView: %s", e)
            return Response(
                {
                    'error': 'No se pudo obtener la lista de gimnasios.',
                    'detalle': str(e),
                    'sedes': []
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )