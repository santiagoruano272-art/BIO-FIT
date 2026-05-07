from django.urls import path
from . import views_rutinas  # Importamos tus vistas reales

app_name = 'routines'

urlpatterns = [
    # Esta ruta cargará el formulario para generar la rutina
    path('generar/', views_rutinas.routine_generator_view, name='generator'),
    
    # Esta ruta servirá para procesar la petición de la IA vía AJAX
    path('api/generate/', views_rutinas.generate_routine_api, name='api_generate'),
]