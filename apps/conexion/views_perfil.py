"""
views_perfil.py  –  BIO-FIT
Autenticación unificada: usa sesión Django en lugar de FirebaseAuthentication/Bearer token.
"""

import logging
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny

from services.firebase_client import FirebaseClient

logger = logging.getLogger(__name__)
firebase = FirebaseClient()


# ── UTILIDAD: obtener uid desde sesión Django ─────────────────────────────────

def _get_uid(request) -> str | None:
    uid = request.session.get('user_uid')
    if uid:
        return uid

    # Fallback 1: reconstruir sesión desde email del usuario Django autenticado
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
                uid    = doc.id
                perfil = doc.to_dict() or {}
                request.session['user_uid'] = uid
                request.session['user_rol'] = perfil.get('rol', 'atleta')
                gym_id = perfil.get('gym_id')
                if gym_id:
                    request.session['gym_id'] = gym_id
                request.session.modified = True
                return uid
        except Exception as e:
            logger.error("Error reconstruyendo sesión desde Django user: %s", e)

    # Fallback 2: reconstruir sesión desde Firebase idToken en header Authorization
    # Esto resuelve el caso donde el frontend tiene token pero no cookie de sesión Django
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        id_token = auth_header.split(' ', 1)[1]
        try:
            from services.firebase_client import verify_firebase_token
            decoded = verify_firebase_token(id_token)
            if decoded:
                uid   = decoded['uid']
                email = decoded.get('email', '')
                perfil = firebase.get_user_profile(uid) or {}

                # Si no existe el perfil aún, buscarlo en gimnasios como fallback
                if not perfil and email:
                    gym_docs = (
                        firebase.db.collection('gimnasios')
                        .where('email', '==', email)
                        .limit(1)
                        .stream()
                    )
                    for doc in gym_docs:
                        gym_data = doc.to_dict()
                        perfil = {
                            'uid':    uid,
                            'rol':    gym_data.get('rol', 'admin'),
                            'gym_id': doc.id,
                            'email':  email,
                        }
                        firebase.save_user_profile(uid, {**perfil, 'must_change_password': False})
                        break

                if perfil:
                    request.session['user_uid'] = uid
                    request.session['user_rol'] = perfil.get('rol', 'atleta')
                    gym_id = perfil.get('gym_id')
                    if gym_id:
                        request.session['gym_id'] = gym_id
                    request.session.modified = True
                    logger.info("Sesión reconstruida desde Bearer token para uid=%s", uid)
                    return uid
        except Exception as e:
            logger.warning("No se pudo reconstruir sesión desde Bearer token: %s", e)

    return None


# ── MIXIN: autenticación por sesión Django ────────────────────────────────────

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


# ── PÁGINA HTML  →  GET /perfil/ ─────────────────────────────────────────────

@login_required
def perfil_page(request):
    return render(request, 'users/perfil.html')


# ── API: LEER Y ACTUALIZAR PERFIL  →  GET|PUT /api/perfil/ ───────────────────

@method_decorator(csrf_exempt, name='dispatch')
class PerfilView(SesionMixin, APIView):

    def get(self, request):
        uid, err = self._require_uid(request)
        if err:
            return err

        try:
            perfil     = firebase.get_user_profile(uid) or {}
            gym_id     = perfil.get('gym_id')
            gym_nombre = gym_ubicacion = None

            if gym_id:
                # FIX: usa el método centralizado que aprovecha el caché
                gym = firebase.get_gym_by_id(gym_id)
                if gym:
                    gym_nombre    = gym.get('nombre', gym_id)
                    gym_ubicacion = gym.get('ubicacion', '')
                else:
                    gym_nombre = f'Gimnasio no encontrado ({gym_id})'

            return Response({
                'nombre':        perfil.get('nombre', ''),
                'sobrenombre':   perfil.get('sobrenombre', ''),
                'avatar_url':    perfil.get('avatar_url', ''),
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

        datos    = {}
        nombre   = request.data.get('nombre', '').strip()
        sobrenombre = request.data.get('sobrenombre', '').strip()
        avatar_url = request.data.get('avatar_url', '').strip()
        email    = request.data.get('email', '').strip().lower()  # FIX: normalizar email
        telefono = request.data.get('telefono', '').strip()
        nivel    = request.data.get('nivel', '').strip().lower()

        if nombre:
            datos['nombre'] = nombre
        if sobrenombre:
            datos['sobrenombre'] = sobrenombre
        if avatar_url:
            # Validar tamaño del Base64 en el backend como segunda línea de defensa.
            # Base64 representa 3 bytes en 4 caracteres → tamaño real ≈ len * 3/4
            size_kb = len(avatar_url) * 3 / 4 / 1024
            if size_kb > 900:
                return Response(
                    {'error': f'La imagen pesa ~{int(size_kb)} KB. El máximo permitido es 900 KB. '
                               'Usa la función de recorte o elige una imagen más pequeña.'},
                    status=400,
                )
            if not avatar_url.startswith('data:image/'):
                return Response({'error': 'Formato de imagen no válido.'}, status=400)
            datos['avatar_url'] = avatar_url
        if telefono:
            datos['telefono'] = telefono
        if email:
            if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
                return Response({'error': 'Correo electrónico no válido.'}, status=400)
            datos['email'] = email
        if nivel:
            niveles_validos = ['principiante', 'novato', 'experto']
            if nivel not in niveles_validos:
                return Response({'error': f'Nivel no válido. Debe ser uno de: {", ".join(niveles_validos)}'}, status=400)
            datos['nivel'] = nivel

        if not datos:
            return Response({'error': 'No se proporcionaron datos para actualizar.'}, status=400)

        # FIX: validar que nombre no sea solo espacios si viene en el body
        if 'nombre' in datos and not datos['nombre']:
            return Response({'error': 'El nombre no puede estar vacío.'}, status=400)

        try:
            firebase.db.collection('users').document(uid).set(datos, merge=True)
            return Response({'message': 'Perfil actualizado correctamente.', **datos})
        except Exception as e:
            logger.error("Error actualizando perfil uid=%s: %s", uid, e)
            return Response({'error': str(e)}, status=500)


# ── API: LISTAR GIMNASIOS  →  GET /api/gimnasios/?q=<query> ──────────────────

@method_decorator(csrf_exempt, name='dispatch')
class GimnasioBuscadorView(SesionMixin, APIView):
    """
    Devuelve la lista de gimnasios registrados, con filtro opcional por nombre
    o ubicación. No requiere uid — solo sesión Django activa.
    """

    def get(self, request):
        tiene_sesion = (
            bool(request.session.get('user_uid'))
            or request.user.is_authenticated
        )
        if not tiene_sesion:
            return Response({'error': 'No autenticado.'}, status=401)

        q = request.query_params.get('q', '').strip().lower()

        try:
            # FIX: get_all_gyms() usa caché — no lanza N lecturas a Firestore
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


# ── API: VINCULAR / DESVINCULAR GIMNASIO  →  POST|DELETE /api/perfil/gimnasio/ ─

@method_decorator(csrf_exempt, name='dispatch')
class GimnasioVinculacionView(SesionMixin, APIView):

    def post(self, request):
        uid, err = self._require_uid(request)
        if err:
            return err

        gym_id = request.data.get('gym_id', '').strip()
        if not gym_id:
            return Response({'error': 'gym_id es requerido.'}, status=400)

        # FIX: usa get_gym_by_id centralizado (con caché)
        gym = firebase.get_gym_by_id(gym_id)
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