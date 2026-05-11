# apps/rutinas/urls.py
from django.urls import path
from . import views_rutinas

app_name = 'routines'

urlpatterns = [
    # Esta es la ruta que carga la página (el formulario)
    path('generar/', views_rutinas.routine_generator_view, name='generate'),
    
    # Esta es la ruta que procesa la IA (la que el JavaScript busca)
    path('api/generar/', views_rutinas.routine_generator_view, name='api_generate'),
]