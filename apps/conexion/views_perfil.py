"""
views_perfil.py  –  BIO-FIT
Autenticación unificada: usa sesión Django (igual que views_rutinas.py)
en lugar de FirebaseAuthentication/Bearer token.
"""

import logging
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny

from services.firebase_client import FirebaseClient

logger = logging.getLogger(__name__)
firebase = FirebaseClient()


# ─────────────────────────────────────────────────────────────────
# UTILIDAD: obtener uid desde la sesión Django
# ─────────────────────────────────────────────────────────────────
def _get_uid(request) -> str | None:
    uid = request.session.get('user_uid')
    if uid:
        return uid

    # Fallback: reconstruir sesión desde email del usuario Django
    if request.user.is_authenticated:
        email = request.user.username
        try:
            docs = (
                firebase.db.collection('users')
                .where('email', '==', email)
                .limit(1)
                .stream()
            )
            for doc in docs:
                uid = doc.id
                perfil = doc.to_dict() or {}
                request.session['user_uid'] = uid
                request.session['user_rol'] = perfil.get('rol', 'atleta')
                gym_id = perfil.get('gym_id')
                if gym_id:
                    request.session['gym_id'] = gym_id
                request.session.modified = True
                return uid
        except Exception as e:
            logger.error("Error reconstruyendo sesión: %s", e)
    return None


# ─────────────────────────────────────────────────────────────────
# UTILIDAD: buscar un gimnasio por su campo gym_id
# ─────────────────────────────────────────────────────────────────
def _buscar_gym_por_id(gym_id: str) -> dict | None:
    try:
        gyms = firebase.get_all_gyms() or []
        for g in gyms:
            if g.get('gym_id') == gym_id or g.get('id') == gym_id:
                return g
    except Exception as e:
        logger.error("Error en _buscar_gym_por_id: %s", e)
    return None


# ─────────────────────────────────────────────────────────────────
# MIXIN: autenticación por sesión Django, sin Bearer token
# ─────────────────────────────────────────────────────────────────
class SesionMixin:
    authentication_classes = []
    permission_classes     = [AllowAny]

    def _require_uid(self, request):
        """Devuelve (uid, None) o (None, Response 401)."""
        uid = _get_uid(request)
        if not uid:
            return None, Response(
                {'error': 'Sesión inválida. Inicia sesión de nuevo.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        return uid, None


# ─────────────────────────────────────────────────────────────────
# PÁGINA HTML  →  GET /perfil/
# ─────────────────────────────────────────────────────────────────
@login_required
def perfil_page(request):
    return render(request, 'users/perfil.html')


# ─────────────────────────────────────────────────────────────────
# API: LEER Y ACTUALIZAR PERFIL  →  GET|PUT /api/perfil/
# ─────────────────────────────────────────────────────────────────
@method_decorator(csrf_exempt, name='dispatch')
class PerfilView(SesionMixin, APIView):

    def get(self, request):
        uid, err = self._require_uid(request)
        if err:
            return err

        try:
            perfil = firebase.get_user_profile(uid) or {}
            gym_id = perfil.get('gym_id')
            gym_nombre = gym_ubicacion = None

            if gym_id:
                gym = _buscar_gym_por_id(gym_id)
                if gym:
                    gym_nombre    = gym.get('nombre', gym_id)
                    gym_ubicacion = gym.get('ubicacion', '')
                else:
                    gym_nombre = f"Gimnasio no encontrado ({gym_id})"

            return Response({
                'nombre':        perfil.get('nombre', ''),
                'email':         perfil.get('email', ''),
                'telefono':      perfil.get('telefono', ''),
                'nivel':         perfil.get('nivel', 'principiante'),
                'rol':           perfil.get('rol', 'atleta'),
                'gym_id':        gym_id,
                'gym_nombre':    gym_nombre,
                'gym_ubicacion': gym_ubicacion,
            })
        except Exception as e:
            logger.error("Error en PerfilView.get uid=%s: %s", uid, e)
            return Response({'error': str(e)}, status=500)

    def put(self, request):
        import re
        uid, err = self._require_uid(request)
        if err:
            return err

        datos = {}
        nombre   = request.data.get('nombre', '').strip()
        email    = request.data.get('email', '').strip()
        telefono = request.data.get('telefono', '').strip()

        if nombre:   datos['nombre']   = nombre
        if telefono: datos['telefono'] = telefono
        if email:
            if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
                return Response({'error': 'Correo electrónico no válido.'}, status=400)
            datos['email'] = email

        if not datos:
            return Response({'error': 'No se proporcionaron datos para actualizar.'}, status=400)

        try:
            firebase.db.collection('users').document(uid).set(datos, merge=True)
            return Response({'message': 'Perfil actualizado correctamente.', **datos})
        except Exception as e:
            logger.error("Error actualizando perfil uid=%s: %s", uid, e)
            return Response({'error': str(e)}, status=500)


# ─────────────────────────────────────────────────────────────────
# API: LISTAR GIMNASIOS  →  GET /api/gimnasios/?q=<query>
# ─────────────────────────────────────────────────────────────────
@method_decorator(csrf_exempt, name='dispatch')
class GimnasioBuscadorView(SesionMixin, APIView):
    """
    NO verifica uid — solo requiere que haya sesión Django activa
    (user_uid en sesión OR usuario Django autenticado).
    Esto evita el 401 cuando el buscador se monta en una URL
    distinta al módulo de perfil.
    """

    def get(self, request):
        # Verificación ligera: sesión Django o user_uid en sesión
        # No usamos _require_uid para no depender de Firestore en este endpoint
        tiene_sesion = (
            bool(request.session.get('user_uid'))
            or request.user.is_authenticated
        )
        if not tiene_sesion:
            return Response({'error': 'No autenticado.'}, status=401)

        q = request.query_params.get('q', '').strip().lower()

        try:
            gyms_raw = firebase.get_all_gyms() or []
            sedes = []
            for g in gyms_raw:
                gym_id    = g.get('gym_id') or g.get('id')
                nombre    = g.get('nombre', '')
                ubicacion = g.get('ubicacion', '')

                if not gym_id:
                    continue
                if q and q not in nombre.lower() and q not in ubicacion.lower():
                    continue

                sedes.append({
                    'id':        gym_id,
                    'nombre':    nombre,
                    'ubicacion': ubicacion,
                })

            return Response(sedes)

        except Exception as e:
            logger.error("Error en GimnasioBuscadorView: %s", e)
            return Response(
                {'error': 'No se pudo obtener la lista de gimnasios.', 'detalle': str(e)},
                status=503,
            )


# ─────────────────────────────────────────────────────────────────
# API: VINCULAR / DESVINCULAR GIMNASIO  →  POST|DELETE /api/perfil/gym/
# ─────────────────────────────────────────────────────────────────
@method_decorator(csrf_exempt, name='dispatch')
class GimnasioVinculacionView(SesionMixin, APIView):

    def post(self, request):
        uid, err = self._require_uid(request)
        if err:
            return err

        gym_id = request.data.get('gym_id', '').strip()
        if not gym_id:
            return Response({'error': 'gym_id es requerido.'}, status=400)

        gym = _buscar_gym_por_id(gym_id)
        if not gym:
            return Response(
                {'error': 'El gimnasio seleccionado no existe o fue eliminado.'},
                status=404,
            )

        gym_nombre    = gym.get('nombre', gym_id)
        gym_ubicacion = gym.get('ubicacion', '')

        try:
            firebase.db.collection('users').document(uid).set(
                {'gym_id': gym_id}, merge=True
            )
            # Actualizar sesión para que la próxima generación use el inventario correcto
            request.session['gym_id'] = gym_id
            request.session.modified  = True

            return Response({
                'message':       f'Vinculado a "{gym_nombre}" exitosamente.',
                'gym_id':        gym_id,
                'gym_nombre':    gym_nombre,
                'gym_ubicacion': gym_ubicacion,
            })
        except Exception as e:
            logger.error("Error vinculando gym uid=%s: %s", uid, e)
            return Response({'error': str(e)}, status=500)

    def delete(self, request):
        uid, err = self._require_uid(request)
        if err:
            return err

        try:
            from google.cloud.firestore_v1 import DELETE_FIELD
            firebase.db.collection('users').document(uid).update(
                {'gym_id': DELETE_FIELD}
            )
            request.session.pop('gym_id', None)
            request.session.modified = True

            return Response({'message': 'Desvinculado del gimnasio correctamente.'})
        except Exception as e:
            logger.error("Error desvinculando gym uid=%s: %s", uid, e)
            return Response({'error': str(e)}, status=500)