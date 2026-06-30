from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.models import User
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime, timedelta

from apps.conexion.auth import login_user, confirmar_cambio_password, cambiar_password_provisional, ROL_MAP
from services.firebase_client import FirebaseClient

firebase = FirebaseClient()


def _calcular_metricas_dia_real(dia_data: dict) -> dict:
    """
    Calcula métricas REALES basadas en los ejercicios de la rutina.
    """
    calorias_total = 0
    tiempo_total = 0
    musculos_trabajados = set()
    regiones = set()

    ejercicio_map = {
        'sentadilla': {'cal': 6, 'musculos': 'Glúteos, Cuádriceps', 'regiones': ['glutes','quads']},
        'peso muerto': {'cal': 7, 'musculos': 'Espalda, Glúteos', 'regiones': ['back','glutes']},
        'press de banca': {'cal': 5, 'musculos': 'Pecho, Tríceps', 'regiones': ['chest','triceps']},
        'press': {'cal': 5, 'musculos': 'Pecho, Tríceps', 'regiones': ['chest','triceps']},
        'dominada': {'cal': 7, 'musculos': 'Espalda, Bíceps', 'regiones': ['back','biceps']},
        'remo': {'cal': 6, 'musculos': 'Espalda, Bíceps', 'regiones': ['back','biceps']},
        'flexión': {'cal': 4, 'musculos': 'Pecho, Tríceps', 'regiones': ['chest','triceps']},
        'fondos': {'cal': 5, 'musculos': 'Pecho, Tríceps', 'regiones': ['chest','triceps']},
        # Empuje tren superior (variantes)
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

    # Procesar calentamiento (5 min calentamiento general)
    if dia_data.get('calentamiento'):
        tiempo_total += 5
        calorias_total += 2 * 5  # 2 cal/min en calentamiento

    # Procesar entrenamiento principal
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
                mins = float(reps_raw.split()[0])
                reps_avg = None
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
        for ej_key, ej_data in ejercicio_map.items():
            if ej_key in nombre_ej:
                cal_por_min = ej_data['cal']
                musculos_trabajados.add(ej_data['musculos'])
                for r in ej_data.get('regiones', []):
                    regiones.add(r)
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

    # Procesar estiramiento (5 min por defecto)
    if dia_data.get('estiramiento'):
        tiempo_total += 5

    if not musculos_trabajados:
        musculos_trabajados.add('Cuerpo general')

    return {
        'calorias': int(calorias_total),
        'tiempo': tiempo_total,
        'musculos': ', '.join(list(musculos_trabajados)[:3]),
        'muscle_regions': list(regiones),
    }


# ── VISTAS HTML ───────────────────────────────────────────────────────────────

def landing_page(request):
    context = {
        'rutina_calorias': 0,
        'rutina_tiempo': 0,
        'rutina_musculos': 'Sin datos',
    }
    
    # Intentar obtener datos reales de la rutina del usuario
    try:
        # Si hay un preview reciente en sesión (rutina creada/guardada hace poco), usarlo inmediatamente
        preview = request.session.get('ultimo_rutina_preview')
        if preview:
            context.update({
                'rutina_calorias': preview.get('calorias', 0),
                'rutina_tiempo': preview.get('tiempo', 0),
                'rutina_musculos': preview.get('musculos', 'Sin datos'),
            })
            # No hacemos return aquí: aún permitimos intentar cargar desde Firebase si el usuario ya tiene rutinas

        user_uid = request.session.get('user_uid')
        if user_uid:
            docs = firebase.get_user_routines(user_uid)
            if docs:
                # Tomar la rutina más reciente
                routine_data = docs[0].get('routine', {})
                
                if routine_data and 'dias' in routine_data and routine_data['dias']:
                    # Usar el primer día como referencia
                    primer_dia = routine_data['dias'][0]
                    metricas = _calcular_metricas_dia_real(primer_dia)
                    
                    context.update({
                        'rutina_calorias': metricas['calorias'],
                        'rutina_tiempo': metricas['tiempo'],
                        'rutina_musculos': metricas['musculos'],
                    })
    except Exception as e:
        print(f"[BIO-FIT] Error cargando rutina en landing: {e}")
    
    return render(request, 'landing.html', context)


def login_page(request):
    return render(request, 'users/login.html')


def cambiar_password_page(request):
    """
    Vista que se muestra cuando el admin inicia sesión por primera vez
    con contraseña provisional. Solo accesible si hay un uid bloqueado
    en sesión.
    """
    if not request.session.get('uid_pending_password_change'):
        return redirect('login')
    return render(request, 'users/cambiar_password.html')


# ── LOGIN (API) ────────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    email    = request.data.get('email', '').strip().lower()  # FIX: normalizar a minúsculas
    password = request.data.get('password', '')

    if not email or not password:
        return Response(
            {'error': 'Email y contraseña son requeridos.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    result = login_user(email, password)

    # Contraseña provisional detectada — bloquear y redirigir
    if result.get('must_change_password'):
        request.session['uid_pending_password_change']   = result.get('uid')
        request.session['email_pending_password_change'] = email
        return Response(
            {
                'must_change_password': True,
                'redirect':             '/cambiar-password/',
                'error':                result['error'],
            },
            status=status.HTTP_200_OK,
        )

    if 'error' in result:
        return Response(
            {'error': 'Credenciales inválidas.'},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    try:
        user, _ = User.objects.get_or_create(
            username=email,
            defaults={'email': email},
        )

        # Normalizar rol legacy ('gym_owner' → 'admin')
        rol_raw = result.get('rol', 'admin')
        rol     = ROL_MAP.get(rol_raw, rol_raw)

        request.session['user_uid'] = result['uid']
        request.session['user_rol'] = rol
        request.session['gym_id']   = result.get('gym_id')

        login(request, user)

        return Response(
            {
                'token':    result.get('idToken'),
                'uid':      result['uid'],
                'email':    email,
                'rol':      rol,
                'gym_id':   result.get('gym_id'),
                'redirect': '/inventory/dashboard/',
                'message':  'Login exitoso',
            },
            status=status.HTTP_200_OK,
        )

    except Exception as e:
        import logging
        logging.getLogger(__name__).error("Error en login_view: %s", e)
        return Response(
            {'error': 'Error interno al procesar la sesión.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# ── CONFIRMAR CAMBIO DE CONTRASEÑA (API) ──────────────────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
def confirmar_password_view(request):
    """
    El admin envía su contraseña anterior (provisional) y la nueva contraseña
    desde el aviso bloqueante de primer ingreso. Verifica, actualiza en
    Firebase Auth, limpia el flag must_change_password y cierra la sesión
    para que vuelva a iniciar sesión con la contraseña definitiva.
    """
    uid   = request.session.get('uid_pending_password_change')
    email = request.session.get('email_pending_password_change')

    if not uid or not email:
        return Response(
            {'error': 'No hay una sesión de cambio de contraseña activa.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    antigua_password = request.data.get('antigua_password', '')
    nueva_password    = request.data.get('nueva_password', '')

    if not antigua_password or not nueva_password:
        return Response(
            {'error': 'Debes ingresar la contraseña anterior y la nueva contraseña.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if len(nueva_password) < 8:
        return Response(
            {'error': 'La nueva contraseña debe tener al menos 8 caracteres.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    resultado = cambiar_password_provisional(email, antigua_password, nueva_password)

    if 'error' in resultado:
        return Response({'error': resultado['error']}, status=status.HTTP_400_BAD_REQUEST)

    # Limpia toda la sesión: fuerza a volver a iniciar sesión con la nueva contraseña
    request.session.flush()

    return Response(
        {
            'success':  True,
            'redirect': '/login/',
            'message':  'Contraseña actualizada. Ya puedes iniciar sesión con tu nueva contraseña.',
        },
        status=status.HTTP_200_OK,
    )