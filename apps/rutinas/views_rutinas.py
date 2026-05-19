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
}

# Claves que nunca son bloques de ejercicios
_CLAVES_IGNORAR = {
    'metadata', 'objetivo', 'nivel', 'status', 'success',
    'dias', 'days', 'info', 'resumen', 'summary',
}


def _extraer_nombre(ej: dict) -> str:
    """Busca el nombre real del ejercicio en cualquier clave posible."""
    for clave in _CLAVES_NOMBRE:
        valor = ej.get(clave, '')
        if valor and str(valor).strip():
            nombre = str(valor).strip()
            # Rechazar nombres genéricos que la IA pueda colar
            if nombre.lower() not in {
                'ejercicio', 'ejercicio personalizado', 'exercise',
                'nombre', 'name', 'n/a', '', 'null', 'none',
            }:
                return nombre
    # Último recurso: buscar cualquier clave cuyo valor sea un string largo
    for k, v in ej.items():
        if isinstance(v, str) and len(v) > 4 and k not in {
            'series', 'repeticiones', 'reps', 'descanso', 'rest', 'nota', 'note', 'tips'
        }:
            return v.strip()
    return 'Ejercicio sin nombre'


def normalizar_rutina(raw: dict) -> dict:
    """
    Convierte cualquier estructura JSON que devuelva la IA al formato estándar
    que espera generador.html:
      { "Calentamiento": [...], "Entrenamiento Principal": [...], "Estiramiento y Enfriamiento": [...] }
    """
    # Desempaquetar un nivel si viene envuelto
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            return {}

    for wrapper in ('routine', 'rutina', 'data', 'resultado'):
        if wrapper in raw and isinstance(raw[wrapper], dict):
            raw = raw[wrapper]
            break

    rutina_limpia = {}

    for bloque_key, ejercicios in raw.items():
        if bloque_key.lower() in _CLAVES_IGNORAR:
            continue
        if not isinstance(ejercicios, list):
            continue

        nombre_bloque = _MAPEO_BLOQUES.get(
            bloque_key.lower(),
            bloque_key.replace('_', ' ').capitalize()
        )

        lista_limpia = []
        for ej in ejercicios:
            if not isinstance(ej, dict):
                continue

            lista_limpia.append({
                'ejercicio':    _extraer_nombre(ej),
                'series':       str(ej.get('series') or ej.get('sets') or '3'),
                'repeticiones': str(ej.get('repeticiones') or ej.get('reps') or ej.get('repetitions') or '12'),
                'descanso':     str(ej.get('descanso') or ej.get('rest') or ej.get('break') or '60 seg'),
                'nota':         str(ej.get('nota') or ej.get('note') or ej.get('tips') or ''),
            })

        if lista_limpia:
            rutina_limpia[nombre_bloque] = lista_limpia

    return rutina_limpia


# ── Vistas ─────────────────────────────────────────────────────────────────────

@login_required
def routine_generator_view(request):
    """Renderiza el formulario del generador de rutinas."""
    return render(request, 'rutinas/generador.html')


def generate_routine_api(request):
    """Endpoint POST asíncrono: recibe parámetros, llama a la IA y devuelve JSON."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'error': 'Método no permitido'}, status=405)

    try:
        data = json.loads(request.body)

        # Enriquecer con datos de sesión/perfil si están disponibles
        uid = request.session.get('user_uid')
        if uid:
            perfil = firebase.get_user_profile(uid) or {}
            data.setdefault('edad',   perfil.get('age', ''))
            data.setdefault('peso',   perfil.get('weight_kg', ''))
            data.setdefault('genero', perfil.get('gender', ''))

        print(f"[BIO-FIT] Generando rutina — parámetros: {data}")

        result = routine_generator.generate_routine(data)

        if result.get('success') and 'routine' in result:
            rutina_procesada = normalizar_rutina(result['routine'])

            if not rutina_procesada:
                print("[BIO-FIT] normalizar_rutina devolvió vacío. Raw:", result['routine'])
                return JsonResponse({
                    'status': 'error',
                    'error': 'La IA generó datos pero no se pudo interpretar la estructura.'
                }, status=400)

            print(f"[BIO-FIT] Rutina lista — bloques: {list(rutina_procesada.keys())}")
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
    """Guarda la rutina generada en Firestore."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    try:
        rutina_data = json.loads(request.body)
        user_uid = request.session.get('user_uid')

        if not user_uid:
            return JsonResponse({'error': 'Sesión inválida. Inicia sesión de nuevo.'}, status=401)

        firebase.save_routine(user_id=user_uid, routine_data=rutina_data)

        return JsonResponse({'success': True, 'message': 'Rutina guardada correctamente.'})

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Datos inválidos.'}, status=400)
    except Exception as e:
        print(f"[BIO-FIT] Error al guardar rutina: {e}")
        return JsonResponse({'error': str(e)}, status=500)