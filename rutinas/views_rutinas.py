# ============================================================
#  BIO-FIT — apps/routines/views.py
# ============================================================

import json
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages

from .ai_generator import routine_generator
from .forms import RoutineRequestForm
from services.firebase_client import FirebaseClient

firebase = FirebaseClient()


@login_required
def routine_generator_view(request):
    """
    Vista principal del generador de rutinas.
    GET: Muestra el formulario de solicitud.
    POST: Procesa el formulario y llama a la IA.
    """
    if request.method == 'POST':
        form = RoutineRequestForm(request.POST)
        if form.is_valid():
            user_data = form.cleaned_data

            # Añadir datos del perfil del usuario
            user_profile = firebase.get_user_profile(request.user.uid)
            if user_profile:
                user_data.update({
                    'age': user_profile.get('age'),
                    'gender': user_profile.get('gender'),
                    'weight_kg': user_profile.get('weight_kg'),
                    'height_cm': user_profile.get('height_cm'),
                })

            # Generar rutina con IA
            result = routine_generator.generate_routine(user_data)

            if result['success']:
                routine = result['routine']

                # Guardar en Firebase
                routine_id = firebase.save_routine(
                    user_id=request.user.uid,
                    routine_data=routine,
                    user_inputs=user_data,
                )

                return redirect('routines:detail', routine_id=routine_id)
            else:
                messages.error(request, result['error'])
        # Si el form es inválido, cae al render de abajo
    else:
        form = RoutineRequestForm()

    return render(request, 'routines/generator.html', {'form': form})


@login_required
def routine_detail_view(request, routine_id):
    """
    Muestra el detalle completo de una rutina generada.
    """
    routine_data = firebase.get_routine(
        user_id=request.user.uid,
        routine_id=routine_id
    )

    if not routine_data:
        messages.error(request, 'Rutina no encontrada.')
        return redirect('routines:list')

    return render(request, 'routines/detail.html', {
        'routine': routine_data['routine'],
        'routine_id': routine_id,
        'created_at': routine_data.get('created_at'),
    })


@login_required
def routine_list_view(request):
    """
    Lista todas las rutinas generadas por el usuario.
    """
    routines = firebase.get_user_routines(request.user.uid)
    return render(request, 'routines/list.html', {'routines': routines})


@login_required
@require_POST
def generate_routine_ajax(request):
    """
    Endpoint AJAX para generación de rutina con indicador de progreso.
    Devuelve JSON con la rutina o el error.
    """
    try:
        data = json.loads(request.body)
        form = RoutineRequestForm(data)

        if not form.is_valid():
            return JsonResponse({
                'success': False,
                'errors': form.errors,
            }, status=400)

        user_data = form.cleaned_data

        # Enriquecer con perfil
        user_profile = firebase.get_user_profile(request.user.uid)
        if user_profile:
            user_data.update({
                'age': user_profile.get('age'),
                'gender': user_profile.get('gender'),
                'weight_kg': user_profile.get('weight_kg'),
                'height_cm': user_profile.get('height_cm'),
            })

        result = routine_generator.generate_routine(user_data)

        if result['success']:
            routine_id = firebase.save_routine(
                user_id=request.user.uid,
                routine_data=result['routine'],
                user_inputs=user_data,
            )
            return JsonResponse({
                'success': True,
                'routine': result['routine'],
                'routine_id': routine_id,
                'redirect_url': f'/routines/{routine_id}/',
            })
        else:
            return JsonResponse({'success': False, 'error': result['error']}, status=500)

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'JSON inválido.'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
