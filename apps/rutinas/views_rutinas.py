import json
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
# CAMBIA ESTA LÍNEA:
from .ai_generator import routine_generator 
from .forms import RoutineRequestForm

@login_required
def routine_generator_view(request):
    if request.method == 'POST':
        if request.content_type == 'application/json':
            try:
                body_unicode = request.body.decode('utf-8')
                data = json.loads(body_unicode)
                
                # Ahora 'routine_generator' ya estará definido porque lo importamos arriba
                result = routine_generator.generate_routine(data)
                return JsonResponse(result)
                
            except Exception as e:
                print(f"DEBUG - Error en vista: {str(e)}")
                return JsonResponse({'success': False, 'error': str(e)}, status=400)
        
        form = RoutineRequestForm(request.POST)
        if form.is_valid():
            result = routine_generator.generate_routine(form.cleaned_data)
            return JsonResponse(result)
    
    return render(request, 'rutinas/generador.html', {'form': RoutineRequestForm()})