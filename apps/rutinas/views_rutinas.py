import json
from django.http import JsonResponse
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from .ai_generator import routine_generator
from services.firebase_client import FirebaseClient

firebase = FirebaseClient()


def _get_uid(request) -> str | None:
    uid = request.session.get('user_uid')
    if uid:
        return uid

    if request.user.is_authenticated:
        email = request.user.username
        try:
            docs = firebase.db.collection('users').where('email', '==', email).limit(1).stream()
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
            print(f"[BIO-FIT] Error reconstruyendo sesión: {e}")

    return None


# ── Claves aceptadas para el nombre del ejercicio ─────────────────────────────
_CLAVES_NOMBRE = [
    'ejercicio', 'nombre', 'exercise', 'name',
    'nombre_ejercicio', 'exercise_name', 'actividad',
]


def _normalizar_ejercicios(lista_ejercicios: list) -> list:
    if not isinstance(lista_ejercicios, list):
        return []
    resultado = []
    for ej in lista_ejercicios:
        if not isinstance(ej, dict):
            continue
        nombre = "Ejercicio sin nombre"
        for clave in _CLAVES_NOMBRE:
            if clave in ej:
                nombre = ej[clave]
                break
        resultado.append({
            'ejercicio':    str(nombre),
            'series':       str(ej.get('series',       '3')),
            'repeticiones': str(ej.get('repeticiones', '10-12')),
            'descanso':     str(ej.get('descanso',     '60 seg')),
            'nota':         str(ej.get('nota',         '')),
        })
    return resultado


def _normalizar_dia(dia_raw: dict) -> dict:
    if not isinstance(dia_raw, dict):
        return {}

    calentamiento = (
        dia_raw.get('calentamiento') or dia_raw.get('warmup') or
        dia_raw.get('warm_up') or []
    )
    principal = (
        dia_raw.get('entrenamiento_principal') or dia_raw.get('main_workout') or
        dia_raw.get('workout') or dia_raw.get('rutina_principal') or []
    )
    estiramiento = (
        dia_raw.get('estiramiento') or dia_raw.get('cooldown') or
        dia_raw.get('cool_down') or dia_raw.get('enfriamiento') or
        dia_raw.get('vuelta_a_la_calma') or []
    )

    return {
        'dia':                     dia_raw.get('dia', ''),
        'enfoque':                 dia_raw.get('enfoque', ''),
        'calentamiento':           _normalizar_ejercicios(calentamiento),
        'entrenamiento_principal': _normalizar_ejercicios(principal),
        'estiramiento':            _normalizar_ejercicios(estiramiento),
    }


def _normalizar_rutina(rutina_raw: dict) -> dict:
    if not isinstance(rutina_raw, dict):
        return {'dias': []}

    if 'dias' in rutina_raw and isinstance(rutina_raw['dias'], list):
        return {'dias': [_normalizar_dia(d) for d in rutina_raw['dias']]}

    if any(k in rutina_raw for k in ('calentamiento', 'warmup', 'entrenamiento_principal', 'main_workout')):
        dia_unico = _normalizar_dia(rutina_raw)
        dia_unico['dia'] = 'Día 1'
        return {'dias': [dia_unico]}

    print(f"[BIO-FIT] Estructura de rutina desconocida. Claves: {list(rutina_raw.keys())}")
    return {'dias': []}


# ── VISTAS HTML ───────────────────────────────────────────────────────────────

@login_required
def routine_generator_view(request):
    return render(request, 'rutinas/generador.html')


@login_required
def routine_detail_view(request):
    user_uid = request.session.get('user_uid')

    if not user_uid:
        return render(request, 'rutinas/detail.html', {
            'sin_rutinas': True,
            'error': 'No se encontró una sesión activa de Firebase.',
        })

    try:
        docs = firebase.get_user_routines(user_uid)

        if not docs:
            return render(request, 'rutinas/detail.html', {'sin_rutinas': True})

        rutinas = []
        for doc in docs:
            routine_data = doc.get('routine', {})
            user_inputs  = doc.get('user_inputs', {})
            created_at   = doc.get('created_at', '')

            if hasattr(created_at, 'strftime'):
                created_at = created_at.strftime('%d/%m/%Y %H:%M')
            elif hasattr(created_at, 'isoformat'):
                created_at = str(created_at)[:16].replace('T', ' ')

            rutina_normalizada = _normalizar_rutina(routine_data) if routine_data else {'dias': []}

            rutinas.append({
                'id':         doc.get('id', ''),
                'dias':       rutina_normalizada.get('dias', []),
                'inputs':     user_inputs,
                'fecha':      created_at,
                'nivel':      user_inputs.get('nivel', '—'),
                'objetivo':   user_inputs.get('objetivo', '—').replace('_', ' '),
                'dias_semana': user_inputs.get('dias', '—'),
            })

        print(f"[BIO-FIT] {len(rutinas)} rutina(s) cargadas para uid={user_uid}")

        return render(request, 'rutinas/detail.html', {
            'rutinas':     rutinas,
            'sin_rutinas': False,
        })

    except Exception as e:
        print(f"[BIO-FIT] Error cargando historial de Firestore: {e}")
        return render(request, 'rutinas/detail.html', {
            'sin_rutinas': True,
            'error':       'Hubo un inconveniente temporal al consultar tus planes.',
        })


# ── APIs JSON ─────────────────────────────────────────────────────────────────

@login_required
def generate_routine_api(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'error': 'Método no permitido'}, status=405)

    try:
        data = json.loads(request.body)

        nivel    = data.get('nivel', 'intermedio')
        objetivo = data.get('objetivo', 'salud_general')
        dias     = data.get('dias', 3)
        lugar    = data.get('lugar', 'gimnasio')
        lesiones = data.get('lesiones', 'ninguna')
        edad     = data.get('edad', '')
        peso     = data.get('peso', '')
        genero   = data.get('genero', '')

        request.session['ultimo_nivel']    = nivel
        request.session['ultimo_objetivo'] = objetivo
        request.session['ultimo_dias']     = dias
        request.session.modified = True

        gym_id     = request.session.get('gym_id')
        inventario = []

        if gym_id:
            inventario = firebase.get_all_equipment(gym_id)
            lugar = 'gimnasio'
            print(f"[BIO-FIT] Inventario cargado — {len(inventario)} equipo(s) del gimnasio {gym_id}")
        else:
            lugar = 'casa'
            print("[BIO-FIT] Sin gimnasio asignado — rutina en casa con peso corporal")

        user_data = {
            'nivel':               nivel,
            'objetivo':            objetivo,
            'dias':                dias,
            'lugar':               lugar,
            'lesiones':            lesiones,
            'edad':                edad,
            'peso':                peso,
            'genero':              genero,
            'inventario_gimnasio': inventario,
        }

        print(
            f"[BIO-FIT] Generando rutina — nivel={nivel} | objetivo={objetivo} | "
            f"días={dias} | lugar={lugar} | equipos={len(inventario)}"
        )

        result = routine_generator.generate_routine(user_data)

        if not result.get('success'):
            error_msg = result.get('error', 'La IA no devolvió un formato válido.')
            print(f"[BIO-FIT] Error de la IA: {error_msg}")
            return JsonResponse({'status': 'error', 'error': error_msg}, status=400)

        rutina_procesada = _normalizar_rutina(result['routine'])
        print(f"[BIO-FIT] Días generados: {len(rutina_procesada.get('dias', []))}")

        return JsonResponse({'status': 'success', 'rutina': rutina_procesada})

    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'error': 'JSON de solicitud inválido.'}, status=400)
    except Exception as e:
        print(f"[BIO-FIT] Excepción crítica: {e}")
        return JsonResponse({'status': 'error', 'error': str(e)}, status=500)


@login_required
def save_routine_api(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    try:
        body     = json.loads(request.body)
        user_uid = request.session.get('user_uid')

        if not user_uid:
            return JsonResponse({'error': 'Sesión inválida. Inicia sesión de nuevo.'}, status=401)

        if 'rutina' in body and isinstance(body['rutina'], dict):
            routine_data = body['rutina']
            user_inputs  = body.get('inputs', {})
        else:
            routine_data = body
            user_inputs  = {}

        user_inputs.setdefault('nivel',    request.session.get('ultimo_nivel',    ''))
        user_inputs.setdefault('objetivo', request.session.get('ultimo_objetivo', ''))
        user_inputs.setdefault('dias',     request.session.get('ultimo_dias',     ''))

        firebase.save_routine(
            user_id=user_uid,
            routine_data=routine_data,
            user_inputs=user_inputs,
        )

        return JsonResponse({'success': True, 'message': 'Rutina guardada correctamente.'})

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Datos inválidos.'}, status=400)
    except Exception as e:
        print(f"[BIO-FIT] Error guardando rutina en Firebase: {e}")
        return JsonResponse({'error': str(e)}, status=500)


# ── NUEVA API: ELIMINAR RUTINA ────────────────────────────────────────────────

@login_required
@require_http_methods(['DELETE'])
def delete_routine_api(request, routine_id: str):
    """
    Elimina una rutina individual del usuario desde Firestore.
    Solo puede eliminar rutinas que le pertenezcan al usuario en sesión.

    DELETE /rutinas/api/eliminar/<routine_id>/
    """
    user_uid = request.session.get('user_uid')

    if not user_uid:
        return JsonResponse({'error': 'Sesión inválida. Inicia sesión de nuevo.'}, status=401)

    if not routine_id or not routine_id.strip():
        return JsonResponse({'error': 'ID de rutina no proporcionado.'}, status=400)

    try:
        # Verificar que la rutina pertenece al usuario antes de eliminar
        doc_ref = (
            firebase.db
            .collection('users')
            .document(user_uid)
            .collection('routines')
            .document(routine_id)
        )
        doc = doc_ref.get()

        if not doc.exists:
            return JsonResponse(
                {'error': 'La rutina no existe o ya fue eliminada.'},
                status=404,
            )

        doc_ref.delete()
        print(f"[BIO-FIT] Rutina eliminada — uid={user_uid} routine_id={routine_id}")

        return JsonResponse({
            'success':    True,
            'message':    'Rutina eliminada correctamente.',
            'routine_id': routine_id,
        })

    except Exception as e:
        print(f"[BIO-FIT] Error eliminando rutina {routine_id} para uid={user_uid}: {e}")
        return JsonResponse({'error': str(e)}, status=500)