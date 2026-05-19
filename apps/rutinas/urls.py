from django.urls import path
from . import views_rutinas

app_name = 'routines'

urlpatterns = [
    # 1. Carga la vista del formulario/página en el navegador (Petición GET normal)
    path('generar/', views_rutinas.routine_generator_view, name='generate'),
    
    # 2. API dedicada que procesa la IA (Petición POST asíncrona)
    path('api/generar/', views_rutinas.generate_routine_api, name='api_generate'),
    
    # 3. API que recibe la rutina armada y la guarda en Firebase
    path('api/save/', views_rutinas.save_routine_api, name='api_save'),
]