import json
from django.http import JsonResponse
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .ai_generator import routine_generator
from services.firebase_client import FirebaseClient

firebase = FirebaseClient()

# ── Claves aceptadas para el nombre del ejercicio ──────────────────────────────
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
    'cooldown':                  'Estiramiento y Enfriamiento',
    'cool_down':                 'Estiramiento y Enfriamiento',
    'enfriamiento':              'Estiramiento y Enfriamiento',
    'vuelta_a_la_calma':         'Estiramiento y Enfriamiento',
}


def _normalizar_ejercicios(lista_ejercicios):
    """
    Toma una lista de ejercicios cruda de la IA y asegura que cada objeto
    tenga exactamente las llaves: 'ejercicio', 'series', 'repeticiones', 'descanso', 'nota'.
    """
    if not isinstance(lista_ejercicios, list):
        return []

    ejercicios_limpios = []
    for ej in lista_ejercicios:
        if not isinstance(ej, dict):
            continue

        # Buscar el nombre del ejercicio en las variantes permitidas
        nombre_detectado = "Ejercicio sin nombre"
        for clave in _CLAVES_NOMBRE:
            if clave in ej:
                nombre_detectado = ej[clave]
                break

        # Limpiar y estructurar de forma segura para la base de datos y plantilla
        ejercicios_limpios.append({
            'ejercicio':    str(nombre_detectado),
            'series':       str(ej.get('series', '3')),
            'repeticiones': str(ej.get('repeticiones', '10-12')),
            'descanso':     str(ej.get('descanso', '60 seg')),
            'nota':         str(ej.get('nota', '')),
        })
    return ejercicios_limpios


def _normalizar_rutina(rutina_raw):
    """Normaliza las llaves de los bloques principales de la IA."""
    if not isinstance(rutina_raw, dict):
        return {}

    rutina_normalizada = {}
    for bloque_ia, ejercicios in rutina_raw.items():
        bloque_limpio = str(bloque_ia).lower().strip()
        nombre_oficial = _MAPEO_BLOQUES.get(bloque_limpio, bloque_ia)
        rutina_normalizada[nombre_oficial] = _normalizar_ejercicios(ejercicios)
        
    return rutina_normalizada


# ── Vistas del Servidor Web (Manejo de Renderizado) ───────────────────────────

@login_required
def routine_generator_view(request):
    """Muestra la página con el formulario/asistente de IA para crear rutinas."""
    return render(request, 'rutinas/generador.html')


@login_required
def routine_detail_view(request):
    """
    Trae el historial completo de rutinas del usuario autenticado desde Firestore
    y las renderiza de manera elegante en el template detail.html.
    """
    user_uid = request.session.get('user_uid')

    if not user_uid:
        return render(request, 'rutinas/detail.html', {
            'sin_rutinas': True,
            'error': 'No se encontró una sesión activa de Firebase.'
        })

    try:
        docs = firebase.get_user_routines(user_uid)

        if not docs:
            return render(request, 'rutinas/detail.html', {
                'sin_rutinas': True,
            })

        # Construir lista de rutinas estructurada para el template
        rutinas = []
        for doc in docs:
            routine_data = doc.get('routine', {})
            user_inputs  = doc.get('user_inputs', {})
            created_at   = doc.get('created_at', '')

            # Formatear la fecha/timestamp de Firestore a formato legible
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

        print(f"[BIO-FIT] {len(rutinas)} rutina(s) cargadas para el usuario {user_uid}")

        return render(request, 'rutinas/detail.html', {
            'rutinas':     rutinas,
            'sin_rutinas': False,
        })

    except Exception as e:
        print(f"[BIO-FIT] Error al cargar el historial desde Firestore: {e}")
        return render(request, 'rutinas/detail.html', {
            'sin_rutinas': True,
            'error': 'Hubo un inconveniente temporal al consultar tus planes.'
        })


# ── Endpoints del Servidor (APIs Asíncronas JSON) ─────────────────────────────

@login_required
def generate_routine_api(request):
    """API que procesa la solicitud del frontend y llama a la IA de Groq."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'error': 'Método no permitido'}, status=405)

    try:
        data = json.loads(request.body)

        request.session['ultimo_nivel'] = data.get('nivel', '')
        request.session['ultimo_objetivo'] = data.get('objetivo', '')
        request.session['ultimo_dias'] = data.get('dias', '')

        # ── Inyectar inventario real del gimnasio del usuario ────────────────
        # Si el usuario tiene un gym_id en sesión, consultamos sus equipos en
        # Firebase y se los pasamos a la IA para que solo use lo disponible.
        gym_id = request.session.get('gym_id')
        lugar  = data.get('lugar', 'gimnasio')

        if gym_id:
            inventario = firebase.get_all_equipment(gym_id)
            data['inventario_gimnasio'] = inventario
            data['lugar'] = 'gimnasio'
            print(f"[BIO-FIT] Inventario cargado — {len(inventario)} equipo(s) del gimnasio {gym_id}")
        elif lugar == 'casa' or not gym_id:
            data['inventario_gimnasio'] = []
            data['lugar'] = 'casa'
            print("[BIO-FIT] Sin gimnasio asignado — rutina en casa con peso corporal")

        print(f"[BIO-FIT] Generando rutina — parámetros: nivel={data.get('nivel')} | objetivo={data.get('objetivo')} | lugar={data.get('lugar')}")
        result = routine_generator.generate_routine(data)

        if result.get('success') and 'routine' in result:
            rutina_procesada = _normalizar_rutina(result['routine'])
            print(f"[BIO-FIT] Rutina lista — bloques: {list(rutina_procesada.keys())}")

        body = json.loads(request.body)
        
        # 1. Extraemos los parámetros dinámicos enviados por el formulario
        nivel = body.get('nivel', 'principiante')
        objetivo = body.get('objetivo', 'salud_general')
        dias = body.get('dias', '3')

        # 2. Respaldamos en sesión (servirá de contexto rápido al guardar)
        request.session['ultimo_nivel'] = nivel
        request.session['ultimo_objetivo'] = objetivo
        request.session['ultimo_dias'] = dias

        print(f"[BIO-FIT] Petición recibida — Nivel: {nivel}, Objetivo: {objetivo}, Días: {dias}")

        # 3. Estructuramos el diccionario que requiere ai_generator.py
        user_data = {
            'nivel': nivel,
            'objetivo': objetivo,
            'dias': dias
        }

        # 4. Solicitamos la generación dinámica al motor Groq
        result = routine_generator.generate_routine(user_data)

        if result.get('success'):
            rutina_original = result.get('routine', {})
            
            # CORRECCIÓN INTEGRADA: Usamos la función nativa '_normalizar_rutina' de este archivo
            rutina_procesada = _normalizar_rutina(rutina_original)


            return JsonResponse({'status': 'success', 'rutina': rutina_procesada})

        error_msg = result.get('error', 'La IA no devolvió un formato válido.')
        print(f"[BIO-FIT] Error de la IA: {error_msg}")
        return JsonResponse({'status': 'error', 'error': error_msg}, status=400)

    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'error': 'JSON de solicitud inválido.'}, status=400)
    except Exception as e:
        print(f"[BIO-FIT] Excepción crítica: {e}")
        return JsonResponse({'status': 'error', 'error': str(e)}, status=500)


@login_required
def save_routine_api(request):
    """API que recibe la rutina ya formateada y la almacena en Firestore."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido.'}, status=405)

    try:
        body = json.loads(request.body)
        user_uid = request.session.get('user_uid')

        if not user_uid:
            return JsonResponse({'error': 'Sesión inválida. Inicia sesión de nuevo.'}, status=401)

        # Si el frontend envía un objeto envoltorio o la rutina directa, lo manejamos de forma segura
        if 'rutina' in body and isinstance(body['rutina'], dict):
            routine_data = body['rutina']
            user_inputs  = body.get('inputs', {})
        else:
            routine_data = body
            user_inputs  = {}

        # Seteamos valores por defecto usando los datos que guardamos previamente en sesión
        user_inputs.setdefault('nivel',    request.session.get('ultimo_nivel', ''))
        user_inputs.setdefault('objetivo', request.session.get('ultimo_objetivo', ''))
        user_inputs.setdefault('dias',     request.session.get('ultimo_dias', ''))

        # Envío a los servicios de FirebaseClient
        firebase.save_routine(
            user_id=user_uid,
            routine_data=routine_data,
            user_inputs=user_inputs,
        )

        return JsonResponse({'success': True, 'message': 'Rutina guardada correctamente.'})

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Datos inválidos.'}, status=400)
    except Exception as e:
        print(f"[BIO-FIT] Error al guardar rutina en Firebase: {e}")
        return JsonResponse({'error': str(e)}, status=500)