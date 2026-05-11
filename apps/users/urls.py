from django.urls import path
from . import views_rutinas

app_name = 'routines'

urlpatterns = [
    # Carga el formulario
    path('generar/', views_rutinas.routine_generator_view, name='generate'),
    
    # Procesa la IA (Nombre corregido para coincidir con el JS del template)
    path('api/generar/', views_rutinas.routine_generator_view, name='api_generate'),
]
