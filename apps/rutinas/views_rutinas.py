import json
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .ai_generator import routine_generator 
from .forms import RoutineRequestForm
# Importamos el cliente de firebase ya inicializado
from apps.conexion.firebase_auth import firebase 

@login_required
def routine_generator_view(request):
    if request.method == 'POST':
        if request.content_type == 'application/json':
            try:
                data = json.loads(request.body)
                
                # 1. Llamada a la IA (Groq llama-3.1-8b-instant)
                result = routine_generator.generate_routine(data)
                
                if result.get('success'):
                    # 2. Obtener UID del usuario autenticado
                    # Intentamos sacarlo del objeto FirebaseUser o de la sesión
                    user_uid = getattr(request.user, 'uid', request.session.get('user_uid'))
                    
                    if user_uid:
                        # 3. Guardar en Firestore: usuarios/{uid}/rutinas_generadas/{id_auto}
                        try:
                            # Preparamos el documento a guardar
                            rutina_a_guardar = result['routine']
                            # Añadimos meta-data para el historial
                            rutina_a_guardar['fecha_creacion'] = firebase.get_timestamp() 
                            
                            # Llamada al cliente de Firebase (Debe estar en tu firebase_client.py)
                            firebase.db.collection('usuarios').document(user_uid)\
                                .collection('rutinas_generadas').add(rutina_a_guardar)
                                
                            result['saved'] = True
                        except Exception as e:
                            print(f"Error persistiendo en Firestore: {e}")
                            result['saved'] = False
                    
                    return JsonResponse(result)
                else:
                    return JsonResponse(result, status=500)
                
            except Exception as e:
                print(f"DEBUG - Error en vista (JSON): {str(e)}")
                return JsonResponse({'success': False, 'error': str(e)}, status=400)
        
        # Manejo de formulario tradicional
        form = RoutineRequestForm(request.POST)
        if form.is_valid():
            result = routine_generator.generate_routine(form.cleaned_data)
            return JsonResponse(result)
    
    return render(request, 'rutinas/generador.html', {'form': RoutineRequestForm()})