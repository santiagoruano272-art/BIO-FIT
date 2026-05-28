# apps/rutinas/views_rutinas.py
# ============================================================
#  BIO-FIT — Vistas de Rutinas
#  CORRECCIÓN: generate_routine_api unificado en un solo flujo.
#  El inventario del gimnasio se inyecta correctamente a la IA.
# ============================================================

import json
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .ai_generator import routine_generator
from services.firebase_client import FirebaseClient
from apps.conexion.auth import login_user

firebase = FirebaseClient()

<<<<<<< Updated upstream

def _get_uid(request) -> str | None:
    """
    Obtiene el user_uid de Firebase de forma robusta.
    Primero busca en sesión (rápido), luego intenta reconstruirla
    desde el username de Django (que guardamos como el email del usuario).
    """
    uid = request.session.get('user_uid')
    if uid:
        return uid

    # Fallback: el usuario está autenticado en Django pero la sesión
    # de Firebase expiró (ej: reinicio del servidor en desarrollo).
    # Reconstruimos buscando el perfil por email en Firestore.
    if request.user.is_authenticated:
        email = request.user.username  # guardamos email como username en login_view
        try:
            docs = firebase.db.collection('users').where('email', '==', email).limit(1).stream()
            for doc in docs:
                uid = doc.id
                # Restaurar sesión completa para próximas peticiones
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

# ── Claves aceptadas para el nombre del ejercicio ──────────────────────────────
=======
# ── Claves aceptadas para el nombre del ejercicio ─────────────────────────────
>>>>>>> Stashed changes
_CLAVES_NOMBRE = [
    'ejercicio', 'nombre', 'exercise', 'name',
    'nombre_ejercicio', 'exercise_name', 'actividad',
]

# ── Mapeo de nombres de bloques de la IA a nombres oficiales ──────────────────
_MAPEO_BLOQUES = {
    'calentamiento':               'Calentamiento',
    'warmup':                      'Calentamiento',
    'warm_up':                     'Calentamiento',
    'warm up':                     'Calentamiento',
    'entrenamiento_principal':     'Entrenamiento Principal',
    'entrenamiento principal':     'Entrenamiento Principal',
    'main_workout':                'Entrenamiento Principal',
    'main_routine':                'Entrenamiento Principal',
    'workout':                     'Entrenamiento Principal',
    'rutina_principal':            'Entrenamiento Principal',
    'estiramiento':                'Estiramiento y Enfriamiento',
    'estiramiento y enfriamiento': 'Estiramiento y Enfriamiento',
<<<<<<< Updated upstream
    'cooldown':                  'Estiramiento y Enfriamiento',
    'cool_down':                 'Estiramiento y Enfriamiento',
    'enfriamiento':              'Estiramiento y Enfriamiento',
}


def _normalizar_ejercicios(lista: list) -> list:
    """Normaliza una lista de ejercicios crudos de la IA."""
    resultado = []
    for ej in lista:
        if not isinstance(ej, dict):
            continue
        nombre = "Ejercicio sin nombre"
        for k in _CLAVES_NOMBRE:
            if k in ej:
                nombre = ej[k]
                break
        resultado.append({
            'ejercicio':    nombre,
            'series':       str(ej.get('series', '3')),
            'repeticiones': str(ej.get('repeticiones', '10')),
            'descanso':     str(ej.get('descanso', '60 seg')),
            'nota':         ej.get('nota', ej.get('recomendacion', '')),
=======
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
>>>>>>> Stashed changes
        })
    return resultado


def _normalizar_rutina(rutina_raw: dict) -> dict:
<<<<<<< Updated upstream
    """
    Soporta dos formatos de respuesta de la IA:
    - NUEVO (multi-día): {"dias": [{"dia": "Día 1", "enfoque": "...", "calentamiento": [...], ...}]}
    - LEGACY (un solo día): {"calentamiento": [...], "entrenamiento_principal": [...], ...}
    Devuelve siempre {"dias": [...]} para que el template itere de forma uniforme.
    """
=======
    """Normaliza las claves de los bloques principales devueltos por la IA."""
>>>>>>> Stashed changes
    if not isinstance(rutina_raw, dict):
        return {'dias': []}

<<<<<<< Updated upstream
    # ── Formato nuevo: multi-día ──────────────────────────────────────────────
    if 'dias' in rutina_raw and isinstance(rutina_raw['dias'], list):
        dias_normalizados = []
        for dia in rutina_raw['dias']:
            if not isinstance(dia, dict):
                continue
            dias_normalizados.append({
                'dia':                    dia.get('dia', 'Día'),
                'enfoque':                dia.get('enfoque', ''),
                'calentamiento':          _normalizar_ejercicios(dia.get('calentamiento', [])),
                'entrenamiento_principal': _normalizar_ejercicios(
                    dia.get('entrenamiento_principal', dia.get('entrenamiento principal', []))
                ),
                'estiramiento':           _normalizar_ejercicios(
                    dia.get('estiramiento', dia.get('estiramiento_y_enfriamiento', []))
                ),
            })
        return {'dias': dias_normalizados}
=======
    rutina_normalizada = {}
    for bloque_ia, ejercicios in rutina_raw.items():
        clave_limpia   = str(bloque_ia).lower().strip()
        nombre_oficial = _MAPEO_BLOQUES.get(clave_limpia, bloque_ia)
        rutina_normalizada[nombre_oficial] = _normalizar_ejercicios(ejercicios)

    return rutina_normalizada
>>>>>>> Stashed changes

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

<<<<<<< Updated upstream

@login_required
def routine_generator_view(request):
    """Renderiza el formulario del generador de rutinas."""
=======
# ── Vistas HTML ───────────────────────────────────────────────────────────────

@login_required
def routine_generator_view(request):
    """Renderiza la página del generador de rutinas con IA."""
>>>>>>> Stashed changes
    return render(request, 'rutinas/generador.html')


@login_required
<<<<<<< Updated upstream
def generate_routine_api(request):
    """API dedicada que procesa la IA (POST asíncrono)."""
=======
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
>>>>>>> Stashed changes
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'error': 'Método no permitido.'}, status=405)

    try:
<<<<<<< Updated upstream
        data = json.loads(request.body)
=======
        # ── 1. Parseo único del body ──────────────────────────────────────────
        body = json.loads(request.body)
>>>>>>> Stashed changes

        nivel    = body.get('nivel',    'principiante')
        objetivo = body.get('objetivo', 'salud_general')
        dias     = body.get('dias',     '3')
        lugar    = body.get('lugar',    'gimnasio')
        lesiones = body.get('lesiones', 'ninguna')
        edad     = body.get('edad',     '')
        peso     = body.get('peso',     '')
        genero   = body.get('genero',   '')

<<<<<<< Updated upstream
        # ── Inyectar inventario real del gimnasio del usuario ────────────────
        # Si el usuario tiene un gym_id en sesión, consultamos sus equipos en
        # Firebase y se los pasamos a la IA para que solo use lo disponible.
        _get_uid(request)  # asegura que la sesión esté reconstruida
        gym_id = request.session.get('gym_id')
        lugar  = data.get('lugar', 'gimnasio')
=======
        # ── 2. Persistir en sesión (para save_routine_api) ───────────────────
        request.session['ultimo_nivel']    = nivel
        request.session['ultimo_objetivo'] = objetivo
        request.session['ultimo_dias']     = dias
        request.session.modified = True

        # ── 3. Resolver inventario del gimnasio ──────────────────────────────
        gym_id    = request.session.get('gym_id')
        inventario = []
>>>>>>> Stashed changes

        if gym_id:
            # Usuario pertenece a un gimnasio registrado → carga el inventario real
            inventario = firebase.get_all_equipment(gym_id)
            lugar      = 'gimnasio'
            print(f"[BIO-FIT] Inventario cargado — {len(inventario)} equipo(s) del gym {gym_id}")
        else:
            # Sin gimnasio asignado → entrenamiento en casa con peso corporal
            lugar = 'casa'
            print("[BIO-FIT] Sin gym_id en sesión — modo casa/peso corporal activado.")

<<<<<<< Updated upstream
        print(f"[BIO-FIT] Generando rutina — parámetros: nivel={data.get('nivel')} | objetivo={data.get('objetivo')} | lugar={data.get('lugar')}")
        result = routine_generator.generate_routine(data)

        if result.get('success') and 'routine' in result:
            rutina_procesada = _normalizar_rutina(result['routine'])
            n_dias = len(rutina_procesada.get('dias', []))
            print(f"[BIO-FIT] Rutina lista — {n_dias} día(s) generados")
            return JsonResponse({'status': 'success', 'rutina': rutina_procesada})

        error_msg = result.get('error', 'La IA no devolvió un formato válido.')
        print(f"[BIO-FIT] Error de la IA: {error_msg}")
        return JsonResponse({'status': 'error', 'error': error_msg}, status=400)
=======
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
>>>>>>> Stashed changes

    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'error': 'JSON de solicitud inválido.'}, status=400)
    except Exception as e:
        print(f"[BIO-FIT] Excepción crítica en generate_routine_api: {e}")
        return JsonResponse({'status': 'error', 'error': str(e)}, status=500)


@login_required
def save_routine_api(request):
<<<<<<< Updated upstream
    """Guarda la rutina generada en Firestore."""
=======
    """Recibe la rutina ya formateada del frontend y la persiste en Firestore."""
>>>>>>> Stashed changes
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    try:
<<<<<<< Updated upstream
        body = json.loads(request.body)
        user_uid = _get_uid(request)
=======
        body     = json.loads(request.body)
        user_uid = request.session.get('user_uid')

>>>>>>> Stashed changes
        if not user_uid:
            return JsonResponse({'error': 'Sesión inválida. Inicia sesión de nuevo.'}, status=401)

        if 'rutina' in body and isinstance(body['rutina'], dict):
            routine_data = body['rutina']
            user_inputs  = body.get('inputs', {})
        else:
            routine_data = body
            user_inputs  = {}

<<<<<<< Updated upstream
        user_inputs.setdefault('nivel',    request.session.get('ultimo_nivel', ''))
=======
        # Rellenar inputs vacíos con los datos guardados en sesión al generar
        user_inputs.setdefault('nivel',    request.session.get('ultimo_nivel',    ''))
>>>>>>> Stashed changes
        user_inputs.setdefault('objetivo', request.session.get('ultimo_objetivo', ''))
        user_inputs.setdefault('dias',     request.session.get('ultimo_dias',     ''))

        # Guardar también el gym_id si está disponible (para auditoría / historial)
        gym_id = request.session.get('gym_id')
        if gym_id:
            user_inputs.setdefault('gym_id', gym_id)

        firebase.save_routine(
            user_id      = user_uid,
            routine_data = routine_data,
            user_inputs  = user_inputs,
        )

        return JsonResponse({'success': True, 'message': 'Rutina guardada correctamente.'})

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Datos inválidos.'}, status=400)
    except Exception as e:
<<<<<<< Updated upstream
        print(f"[BIO-FIT] Error al guardar rutina: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def routine_detail_view(request):
    """
    Recupera TODAS las rutinas del usuario desde la subcolección
    users/{uid}/routines/ y las muestra en detail.html.
    """
    try:
        user_uid = _get_uid(request)
        if not user_uid:
            return redirect('login')

        # ── CORRECCIÓN: leer de la subcolección, NO del perfil ──────────
        # firebase.get_user_routines() devuelve lista de dicts con:
        # { 'id': doc_id, 'routine': {...}, 'user_inputs': {...}, 'created_at': ... }
        docs = firebase.get_user_routines(user_uid, limit=20)

        if not docs:
            return render(request, 'rutinas/detail.html', {
                'rutinas': [],
                'sin_rutinas': True,
            })

        # Construir lista de rutinas para el template
        rutinas = []
        for doc in docs:
            routine_data = doc.get('routine', {})
            user_inputs  = doc.get('user_inputs', {})
            created_at   = doc.get('created_at', '')

            # Formatear fecha si viene como datetime de Firestore
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

        print(f"[BIO-FIT] {len(rutinas)} rutina(s) cargadas para {user_uid}")

        return render(request, 'rutinas/detail.html', {
            'rutinas':     rutinas,
            'sin_rutinas': False,
        })

    except Exception as e:
        print(f"[BIO-FIT] Error al cargar rutinas: {e}")
        return render(request, 'rutinas/detail.html', {
            'error': f'Ocurrió un error al conectar con tu plan de entrenamiento: {str(e)}'
        })
=======
        print(f"[BIO-FIT] Error guardando rutina en Firebase: {e}")
        return JsonResponse({'error': str(e)}, status=500)
>>>>>>> Stashed changes
