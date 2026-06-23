import json
from functools import wraps
from datetime import datetime, date as date_cls, timezone, timedelta
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods
from .ai_generator import routine_generator
from services.firebase_client import FirebaseClient

COL_TZ = timezone(timedelta(hours=-5))

firebase = FirebaseClient()


# ── Decorador propio: reemplaza @login_required para sesión Firebase ──────────

def firebase_login_required(view_func):
    """
    Reemplaza @login_required de Django.
    Verifica que exista 'user_uid' en la sesión (puesto por tu login con Firebase).
    Si no existe, redirige a /login/ (vistas HTML) o devuelve 401 (APIs JSON).
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        uid = request.session.get('user_uid')
        if not uid:
            # Detectar si es una petición API (espera JSON) o una vista HTML
            is_api = request.path.startswith('/rutinas/api/')
            if is_api:
                return JsonResponse({'error': 'Sesión inválida. Inicia sesión de nuevo.'}, status=401)
            return redirect('/login/')
        return view_func(request, *args, **kwargs)
    return wrapper


def _get_uid(request) -> str | None:
    return request.session.get('user_uid')


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

@firebase_login_required
def routine_generator_view(request):
    return render(request, 'rutinas/generador.html')


@firebase_login_required
def routine_detail_view(request):
    user_uid = _get_uid(request)

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
                if created_at.tzinfo is not None:
                    created_at = created_at.astimezone(COL_TZ).strftime('%d/%m/%Y %H:%M')
                else:
                    created_at = created_at.strftime('%d/%m/%Y %H:%M')
            elif hasattr(created_at, 'isoformat'):
                created_at = str(created_at)[:16].replace('T', ' ')

            rutina_normalizada = _normalizar_rutina(routine_data) if routine_data else {'dias': []}

            rutinas.append({
                'id':         doc.get('id', ''),
                'rutina':     rutina_normalizada,
                'inputs':     user_inputs,
                'creado_en':  created_at,
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

@firebase_login_required
def generate_routine_api(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'error': 'Método no permitido'}, status=405)

    try:
        data = json.loads(request.body)

        nivel        = data.get('nivel', 'intermedio')
        objetivo     = data.get('objetivo', 'salud_general')
        dias         = data.get('dias', 3)
        nombres_dias = data.get('nombres_dias', [])
        lugar        = data.get('lugar', 'gimnasio')
        lesiones     = data.get('lesiones', 'ninguna')
        edad         = data.get('edad', '')
        peso         = data.get('peso', '')
        genero       = data.get('genero', '')

        request.session['ultimo_nivel']        = nivel
        request.session['ultimo_objetivo']     = objetivo
        request.session['ultimo_dias']         = dias
        request.session['ultimos_nombres_dias'] = nombres_dias
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
        
        # Replace generic day names with selected ones
        if nombres_dias and len(nombres_dias) > 0:
            for i, dia in enumerate(rutina_procesada.get('dias', [])):
                if i < len(nombres_dias):
                    dia['dia'] = nombres_dias[i]
        
        print(f"[BIO-FIT] Días generados: {len(rutina_procesada.get('dias', []))}")

        return JsonResponse({'status': 'success', 'rutina': rutina_procesada})

    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'error': 'JSON de solicitud inválido.'}, status=400)
    except Exception as e:
        print(f"[BIO-FIT] Excepción crítica: {e}")
        return JsonResponse({'status': 'error', 'error': str(e)}, status=500)


@firebase_login_required
def save_routine_api(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    try:
        body     = json.loads(request.body)
        user_uid = _get_uid(request)

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
        
        # Save selected days (nombres_dias) - first try from request, then from session
        nombres_dias = body.get('inputs', {}).get('nombres_dias', [])
        if not nombres_dias:
            nombres_dias = request.session.get('ultimos_nombres_dias', [])
        user_inputs.setdefault('nombres_dias', nombres_dias)

        now_col = datetime.now(COL_TZ)
        user_inputs.setdefault('start_date',    now_col.strftime('%Y-%m-%d'))
        user_inputs.setdefault('created_at_str', now_col.strftime('%d/%m/%Y %H:%M'))

        firebase.save_routine(
            user_id=user_uid,
            routine_data=routine_data,
            user_inputs=user_inputs,
        )

        # Calcular métricas preview para la landing
        try:
            rutina_normalizada = _normalizar_rutina(routine_data) if routine_data else {'dias': []}
            dias_list = rutina_normalizada.get('dias', [])
            if dias_list:
                metricas_preview = _calcular_metricas_dia(dias_list[0], dias_list[0].get('enfoque'))
            else:
                metricas_preview = {'calorias': 0, 'tiempo': 0, 'musculos': 'Sin datos', 'muscle_regions': []}

            request.session['ultimo_rutina_preview'] = metricas_preview
            request.session.modified = True

        except Exception as e:
            print(f"[BIO-FIT] Error calculando preview de rutina: {e}")

        return JsonResponse({
            'success': True,
            'message': 'Rutina guardada correctamente.',
            'preview': request.session.get('ultimo_rutina_preview', {}),
        })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Datos inválidos.'}, status=400)
    except Exception as e:
        print(f"[BIO-FIT] Error guardando rutina en Firebase: {e}")
        return JsonResponse({'error': str(e)}, status=500)


# ── API: ELIMINAR RUTINA ──────────────────────────────────────────────────────

@firebase_login_required
@require_http_methods(['DELETE'])
def delete_routine_api(request, routine_id: str):
    user_uid = _get_uid(request)

    if not user_uid:
        return JsonResponse({'error': 'Sesión inválida. Inicia sesión de nuevo.'}, status=401)

    if not routine_id or not routine_id.strip():
        return JsonResponse({'error': 'ID de rutina no proporcionado.'}, status=400)

    try:
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


# ── API: RUTINA DEL DÍA ───────────────────────────────────────────────────────

def _enfoque_to_regions(enfoque: str) -> list:
    if not enfoque:
        return []
    e = enfoque.lower()
    regions = set()
    if 'tren superior' in e or 'superior' in e:
        regions.update(['chest', 'shoulders', 'triceps'])
    if 'empuje' in e or 'push' in e or 'press' in e:
        regions.update(['chest', 'shoulders', 'triceps'])
    if 'tirón' in e or 'tiron' in e or 'pull' in e or 'jalón' in e or 'jalon' in e:
        regions.update(['back', 'biceps'])
    if 'pierna' in e or 'piernas' in e or 'lower' in e:
        regions.update(['quads', 'glutes', 'calves'])
    if 'core' in e or 'abdominal' in e:
        regions.update(['core', 'abs'])
    if 'full' in e or 'todo' in e:
        regions.update(['full_body'])
    return list(regions)


def _calcular_metricas_dia(dia_data: dict, enfoque: str = None) -> dict:
    calorias_total = 0
    tiempo_total = 0
    musculos_trabajados = set()
    regiones = set()
    ejercicios_mapeados = []

    ejercicio_map = {
        'sentadilla': {'cal': 6, 'musculos': 'Glúteos, Cuádriceps', 'regiones': ['glutes','quads']},
        'peso muerto': {'cal': 7, 'musculos': 'Espalda, Glúteos', 'regiones': ['back','glutes']},
        'press de banca': {'cal': 5, 'musculos': 'Pecho, Tríceps', 'regiones': ['chest','triceps']},
        'press': {'cal': 5, 'musculos': 'Pecho, Tríceps', 'regiones': ['chest','triceps']},
        'dominada': {'cal': 7, 'musculos': 'Espalda, Bíceps', 'regiones': ['back','biceps']},
        'remo': {'cal': 6, 'musculos': 'Espalda, Bíceps', 'regiones': ['back','biceps']},
        'flexión': {'cal': 4, 'musculos': 'Pecho, Tríceps', 'regiones': ['chest','triceps']},
        'fondos': {'cal': 5, 'musculos': 'Pecho, Tríceps', 'regiones': ['chest','triceps']},
        'press militar': {'cal': 5, 'musculos': 'Hombros, Tríceps', 'regiones': ['shoulders','triceps']},
        'press de hombro': {'cal': 5, 'musculos': 'Hombros, Tríceps', 'regiones': ['shoulders','triceps']},
        'overhead press': {'cal': 5, 'musculos': 'Hombros, Tríceps', 'regiones': ['shoulders','triceps']},
        'elevaciones laterales': {'cal': 3, 'musculos': 'Hombros', 'regiones': ['shoulders']},
        'elevaciones frontales': {'cal': 3, 'musculos': 'Hombros', 'regiones': ['shoulders']},
        'press inclinado': {'cal': 5, 'musculos': 'Pecho, Hombros', 'regiones': ['chest','shoulders']},
        'press plano': {'cal': 5, 'musculos': 'Pecho, Tríceps', 'regiones': ['chest','triceps']},
        'aperturas': {'cal': 4, 'musculos': 'Pecho', 'regiones': ['chest']},
        'fly': {'cal': 4, 'musculos': 'Pecho', 'regiones': ['chest']},
        'bench': {'cal': 5, 'musculos': 'Pecho, Tríceps', 'regiones': ['chest','triceps']},
        'push up': {'cal': 4, 'musculos': 'Pecho, Tríceps', 'regiones': ['chest','triceps']},
        'abdominales': {'cal': 3, 'musculos': 'Abdominales', 'regiones': ['abs']},
        'planchas': {'cal': 4, 'musculos': 'Core, Abdominales', 'regiones': ['core']},
        'corrida': {'cal': 10, 'musculos': 'Glúteos, Cuádriceps', 'regiones': ['glutes','quads']},
        'trote': {'cal': 8, 'musculos': 'Glúteos, Cuádriceps', 'regiones': ['glutes','quads']},
        'bicicleta': {'cal': 8, 'musculos': 'Cuádriceps, Glúteos', 'regiones': ['quads','glutes']},
        'natación': {'cal': 11, 'musculos': 'Todo el cuerpo', 'regiones': ['full_body']},
        'burpee': {'cal': 12, 'musculos': 'Todo el cuerpo', 'regiones': ['full_body']},
        'mountain climbers': {'cal': 9, 'musculos': 'Core, Abdominales', 'regiones': ['core']},
        'saltos': {'cal': 9, 'musculos': 'Glúteos, Cuádriceps', 'regiones': ['glutes','quads']},
        'jalón': {'cal': 5, 'musculos': 'Espalda, Bíceps', 'regiones': ['back','biceps']},
        'curl': {'cal': 4, 'musculos': 'Bíceps', 'regiones': ['biceps']},
        'extensión': {'cal': 4, 'musculos': 'Cuádriceps', 'regiones': ['quads']},
    }

    calentamiento = dia_data.get('calentamiento', []) or []
    if calentamiento:
        tiempo_total += 5
        calorias_total += 2 * 5
        for ej in calentamiento:
            ejercicios_mapeados.append({
                'nombre': ej.get('ejercicio'),
                'tipo': 'calentamiento',
                'series': ej.get('series', ''),
                'repeticiones': ej.get('repeticiones', ''),
                'musculos': '',
                'regiones': [],
            })

    for ejercicio in dia_data.get('entrenamiento_principal', []) or []:
        nombre_ej = str(ejercicio.get('ejercicio', '')).lower()
        try:
            series = int(str(ejercicio.get('series', '3')).split('-')[0])
        except:
            series = 3

        reps_raw = str(ejercicio.get('repeticiones', '')).lower()
        reps_avg = None
        try:
            if 'min' in reps_raw:
                pass
            elif reps_raw and any(ch.isdigit() for ch in reps_raw):
                parts = [p for p in reps_raw.replace(',', '-').split('-') if p.strip()]
                nums = [int(''.join(filter(str.isdigit, p))) for p in parts if any(ch.isdigit() for ch in p)]
                if nums:
                    reps_avg = sum(nums) / len(nums)
        except:
            reps_avg = None

        descanso_raw = str(ejercicio.get('descanso', '')).lower()
        rest_seconds = 60
        try:
            if 'seg' in descanso_raw:
                rest_seconds = int(''.join(filter(str.isdigit, descanso_raw)) or 60)
            elif 'min' in descanso_raw:
                rest_seconds = int(float(''.join(filter(lambda c: c.isdigit() or c=='.', descanso_raw)) or 1) * 60)
            elif descanso_raw and any(ch.isdigit() for ch in descanso_raw):
                rest_seconds = int(''.join(filter(str.isdigit, descanso_raw)) or 60)
        except:
            rest_seconds = 60

        cal_por_min = 6
        musculos_str = ''
        regiones_ej = []
        for ej_key, ej_data in ejercicio_map.items():
            if ej_key in nombre_ej:
                cal_por_min = ej_data['cal']
                musculos_str = ej_data['musculos']
                regiones_ej = ej_data.get('regiones', [])
                break

        tiempo_ej = 0
        if reps_raw and 'min' in reps_raw:
            try:
                tiempo_ej = float(reps_raw.split()[0])
            except:
                tiempo_ej = 0
        elif reps_avg is not None:
            time_per_rep_sec = 4
            tiempo_por_serie_min = (reps_avg * time_per_rep_sec) / 60.0
            descanso_total_min = ((series - 1) * rest_seconds) / 60.0 if series > 1 else 0
            tiempo_ej = series * tiempo_por_serie_min + descanso_total_min
        else:
            tiempo_ej = series * 3

        tiempo_total += tiempo_ej
        calorias_total += cal_por_min * tiempo_ej

        if musculos_str:
            musculos_trabajados.add(musculos_str)
        for r in regiones_ej:
            regiones.add(r)

        ejercicios_mapeados.append({
            'nombre': ejercicio.get('ejercicio'),
            'tipo': 'principal',
            'series': ejercicio.get('series', ''),
            'repeticiones': ejercicio.get('repeticiones', ''),
            'descanso': ejercicio.get('descanso', ''),
            'musculos': musculos_str,
            'regiones': regiones_ej,
            'tiempo_min': tiempo_ej,
            'calorias_estimadas': int(cal_por_min * tiempo_ej),
        })

    estiramiento = dia_data.get('estiramiento', []) or []
    if estiramiento:
        tiempo_total += 5
        for ej in estiramiento:
            ejercicios_mapeados.append({
                'nombre': ej.get('ejercicio'),
                'tipo': 'estiramiento',
                'series': ej.get('series', ''),
                'repeticiones': ej.get('repeticiones', ''),
                'musculos': '',
                'regiones': [],
            })

    if enfoque:
        for r in _enfoque_to_regions(enfoque):
            regiones.add(r)

    if not musculos_trabajados:
        musculos_trabajados.add('Cuerpo general')

    return {
        'calorias': int(calorias_total),
        'tiempo': tiempo_total,
        'musculos': ', '.join(list(musculos_trabajados)[:3]),
        'muscle_regions': list(regiones),
        'ejercicios': ejercicios_mapeados,
    }


@firebase_login_required
def get_routine_day_api(request):
    if request.method != 'GET':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    try:
        user_uid = _get_uid(request)
        date_str = request.GET.get('date', '')

        if not user_uid:
            return JsonResponse({'error': 'Sesión inválida'}, status=401)

        if not date_str:
            return JsonResponse({'error': 'Fecha no proporcionada'}, status=400)

        docs = firebase.get_user_routines(user_uid)

        if not docs:
            return JsonResponse({
                'status': 'no_routine',
                'message': 'No hay rutinas para esta fecha',
                'calorias': 0,
                'tiempo': 0,
                'musculos': 'Sin datos',
                'ejercicios': [],
            })

        rutina_doc = docs[0]
        routine_data = rutina_doc.get('routine', {})
        user_inputs = rutina_doc.get('user_inputs', {})

        if not routine_data:
            return JsonResponse({
                'status': 'no_routine',
                'message': 'Rutina sin datos',
                'calorias': 0,
                'tiempo': 0,
                'musculos': 'Sin datos',
                'ejercicios': [],
            })

        rutina_normalizada = _normalizar_rutina(routine_data)
        dias = rutina_normalizada.get('dias', [])

        if not dias:
            return JsonResponse({
                'status': 'no_routine',
                'message': 'No hay días en la rutina',
                'calorias': 0,
                'tiempo': 0,
                'musculos': 'Sin datos',
                'ejercicios': [],
            })

        try:
            fecha_obj = datetime.strptime(date_str, '%Y-%m-%d')
        except Exception:
            fecha_obj = None

        start_date = None
        try:
            raw_start = user_inputs.get('start_date') if isinstance(user_inputs, dict) else None
            if raw_start:
                try:
                    start_date = datetime.strptime(raw_start, '%Y-%m-%d').date()
                except Exception:
                    try:
                        start_date = raw_start.date() if hasattr(raw_start, 'date') else None
                    except Exception:
                        start_date = None

            if not start_date:
                created_at = rutina_doc.get('created_at')
                if created_at:
                    if hasattr(created_at, 'date'):
                        start_date = created_at.date()
                    else:
                        try:
                            start_date = datetime.strptime(str(created_at)[:10], '%Y-%m-%d').date()
                        except Exception:
                            start_date = None
        except Exception:
            start_date = None

        indice_dia = 0
        if fecha_obj and start_date:
            try:
                delta_days = (fecha_obj.date() - start_date).days
                indice_dia = 0 if delta_days < 0 else delta_days % len(dias)
            except Exception:
                indice_dia = 0
        elif fecha_obj:
            dia_semana = fecha_obj.weekday()
            indice_dia = min(dia_semana, len(dias) - 1)

        dia_seleccionado = dias[indice_dia]
        metricas = _calcular_metricas_dia(dia_seleccionado, dia_seleccionado.get('enfoque'))

        return JsonResponse({
            'status': 'success',
            'calorias': metricas['calorias'],
            'tiempo': metricas['tiempo'],
            'musculos': metricas['musculos'],
            'muscle_regions': metricas.get('muscle_regions', []),
            'ejercicios': metricas.get('ejercicios', []),
            'dia_nombre': dia_seleccionado.get('dia', f'Día {indice_dia + 1}'),
            'enfoque': dia_seleccionado.get('enfoque', ''),
            'nombres_dias': user_inputs.get('nombres_dias', []),
        })

    except Exception as e:
        print(f"[BIO-FIT] Error obteniendo rutina del día: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@firebase_login_required
def get_routine_info_api(request):
    if request.method != 'GET':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    try:
        user_uid = _get_uid(request)
        
        if not user_uid:
            return JsonResponse({'error': 'Sesión inválida'}, status=401)

        docs = firebase.get_user_routines(user_uid)

        if not docs:
            return JsonResponse({
                'status': 'no_routine',
                'nombres_dias': ['Lunes', 'Miércoles', 'Viernes'],
            })

        rutina_doc = docs[0]
        user_inputs = rutina_doc.get('user_inputs', {})

        return JsonResponse({
            'status': 'success',
            'nombres_dias': user_inputs.get('nombres_dias', ['Lunes', 'Miércoles', 'Viernes']),
        })

    except Exception as e:
        print(f"[BIO-FIT] Error obteniendo info de rutina: {e}")
        return JsonResponse({
            'status': 'error',
            'nombres_dias': ['Lunes', 'Miércoles', 'Viernes'],
        })