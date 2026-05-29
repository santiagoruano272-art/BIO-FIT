import json
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .ai_generator import routine_generator
from services.firebase_client import FirebaseClient
from apps.conexion.auth import login_user

firebase = FirebaseClient()

# ── Claves aceptadas para el nombre del ejercicio ─────────────────────────────
_CLAVES_NOMBRE = [
    'ejercicio', 'nombre', 'exercise', 'name',
    'nombre_ejercicio', 'exercise_name', 'actividad',
]

# ── Claves de mapeo de bloques ─────────────────────────────────────────────────
_MAPEO_BLOQUES = {
    'calentamiento':             'Calentamiento',
    'warmup':                    'Calentamiento',
    'warm_up':                   'Calentamiento',
    'warm up':                   'Calentamiento',
    'entrenamiento_principal':   'Entrenamiento Principal',
    'entrenamiento principal':   'Entrenamiento Principal',
    'main_workout':              'Entrenamiento Principal',
    'main_routine':              'Entrenamiento Principal',
    'workout':                   'Entrenamiento Principal',
    'rutina_principal':          'Entrenamiento Principal',
    'estiramiento':              'Estiramiento y Enfriamiento',
    'estiramiento y enfriamiento': 'Estiramiento y Enfriamiento',
    'cooldown':                    'Estiramiento y Enfriamiento',
    'cool_down':                   'Estiramiento y Enfriamiento',
    'enfriamiento':                'Estiramiento y Enfriamiento',
    'vuelta_a_la_calma':           'Estiramiento y Enfriamiento',
}


# ── Helpers de normalización ──────────────────────────────────────────────────

def _normalizar_ejercicios(lista_ejercicios: list) -> list:
    """
    Asegura que cada ejercicio devuelto por la IA tenga exactamente
    las 5 claves requeridas por el template y la base de datos.
    """
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


def _normalizar_rutina(rutina_raw: dict) -> dict:
    """Normaliza las claves de los bloques principales devueltos por la IA."""
    if not isinstance(rutina_raw, dict):
        return {'dias': []}

    rutina_normalizada = {}
    for bloque_ia, ejercicios in rutina_raw.items():
        clave_limpia   = str(bloque_ia).lower().strip()
        nombre_oficial = _MAPEO_BLOQUES.get(clave_limpia, bloque_ia)
        rutina_normalizada[nombre_oficial] = _normalizar_ejercicios(ejercicios)

    return rutina_normalizada

    # ── Formato legacy: un solo día ───────────────────────────────────────────
    dia_unico = {
        'dia':    'Día 1',
        'enfoque': 'Entrenamiento Completo',
        'calentamiento':           _normalizar_ejercicios(rutina_raw.get('calentamiento', [])),
        'entrenamiento_principal': _normalizar_ejercicios(
            rutina_raw.get('entrenamiento_principal', rutina_raw.get('main_workout', []))
        ),
        'estiramiento':            _normalizar_ejercicios(
            rutina_raw.get('estiramiento', rutina_raw.get('cooldown', []))
        ),
    }
    return {'dias': [dia_unico]}

# ── Vistas HTML ───────────────────────────────────────────────────────────────

@login_required
def routine_generator_view(request):
    """Renderiza la página del generador de rutinas con IA."""
    return render(request, 'rutinas/generador.html')


@login_required
def routine_detail_view(request):
    """
    Carga el historial completo de rutinas del usuario desde Firestore
    y lo renderiza en el template de detalle.
    """
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

            rutinas.append({
                'id':       doc.get('id', ''),
                'bloques':  routine_data,
                'inputs':   user_inputs,
                'fecha':    created_at,
                'nivel':    user_inputs.get('nivel', '—'),
                'objetivo': user_inputs.get('objetivo', '—').replace('_', ' '),
                'dias':     user_inputs.get('dias', '—'),
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
    """
    API que genera una rutina personalizada usando la IA de Groq.

    FLUJO UNIFICADO:
    1. Parsea el body UNA SOLA VEZ.
    2. Guarda parámetros en sesión para el guardado posterior.
    3. Si el usuario tiene gym_id en sesión → consulta equipos en Firestore
       e inyecta el inventario real al user_data ANTES de llamar a la IA.
    4. Si entrena en casa o no tiene gym → usa peso corporal.
    5. Llama a la IA UNA SOLA VEZ con todos los datos completos.
    6. Normaliza y devuelve la rutina.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'error': 'Método no permitido'}, status=405)

    try:
        # ── 1. Parseo único del body ──────────────────────────────────────────
        body = json.loads(request.body)

        request.session['ultimo_nivel'] = data.get('nivel', '')
        request.session['ultimo_objetivo'] = data.get('objetivo', '')
        request.session['ultimo_dias'] = data.get('dias', '')

        # ── 2. Persistir en sesión (para save_routine_api) ───────────────────
        request.session['ultimo_nivel']    = nivel
        request.session['ultimo_objetivo'] = objetivo
        request.session['ultimo_dias']     = dias
        request.session.modified = True

        # ── 3. Resolver inventario del gimnasio ──────────────────────────────
        gym_id    = request.session.get('gym_id')
        inventario = []

        if gym_id:
            inventario = firebase.get_all_equipment(gym_id)
            data['inventario_gimnasio'] = inventario
            data['lugar'] = 'gimnasio'
            print(f"[BIO-FIT] Inventario cargado — {len(inventario)} equipo(s) del gimnasio {gym_id}")
        elif lugar == 'casa' or not gym_id:
            data['inventario_gimnasio'] = []
            data['lugar'] = 'casa'
            print("[BIO-FIT] Sin gimnasio asignado — rutina en casa con peso corporal")

        # ── 4. Construir user_data completo para la IA ───────────────────────
        user_data = {
            'nivel':               nivel,
            'objetivo':            objetivo,
            'dias':                dias,
            'lugar':               lugar,
            'lesiones':            lesiones,
            'edad':                edad,
            'peso':                peso,
            'genero':              genero,
            'inventario_gimnasio': inventario,   # ← lista real de Firestore (puede ser [])
        }

        print(
            f"[BIO-FIT] Generando rutina — "
            f"nivel={nivel} | objetivo={objetivo} | días={dias} | "
            f"lugar={lugar} | equipos={len(inventario)}"
        )

        # ── 5. Llamada única a la IA ──────────────────────────────────────────
        result = routine_generator.generate_routine(user_data)

        if not result.get('success'):
            error_msg = result.get('error', 'La IA no devolvió un formato válido.')
            print(f"[BIO-FIT] Error de la IA: {error_msg}")
            return JsonResponse({'status': 'error', 'error': error_msg}, status=400)

        # ── 6. Normalizar y responder ─────────────────────────────────────────
        rutina_procesada = _normalizar_rutina(result['routine'])
        print(f"[BIO-FIT] Rutina generada — bloques: {list(rutina_procesada.keys())}")

        return JsonResponse({'status': 'success', 'rutina': rutina_procesada})

    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'error': 'JSON de solicitud inválido.'}, status=400)
    except Exception as e:
        print(f"[BIO-FIT] Excepción crítica: {e}")
        return JsonResponse({'status': 'error', 'error': str(e)}, status=500)


@login_required
def save_routine_api(request):
    """Recibe la rutina ya formateada del frontend y la persiste en Firestore."""
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

        # Rellenar inputs vacíos con los datos guardados en sesión al generar
        user_inputs.setdefault('nivel',    request.session.get('ultimo_nivel',    ''))
        user_inputs.setdefault('objetivo', request.session.get('ultimo_objetivo', ''))
        user_inputs.setdefault('dias',     request.session.get('ultimo_dias', ''))

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
