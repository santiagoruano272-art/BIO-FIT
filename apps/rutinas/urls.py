from django.urls import path
from . import views_rutinas

app_name = 'routines'

urlpatterns = [
    # 1. Formulario del generador
    path('generar/', views_rutinas.routine_generator_view, name='generate'),
    
    # 2. Vista del detalle de rutina cargada de Firebase
    path('detalle/', views_rutinas.routine_detail_view, name='detail'),
    
    # APIs internas
    path('api/generar/', views_rutinas.generate_routine_api, name='api_generate'),
    path('api/save/', views_rutinas.save_routine_api, name='api_save'),
]