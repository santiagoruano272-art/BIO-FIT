from django.urls import path
from . import views_rutinas

app_name = 'routines'

urlpatterns = [
    # 1. Formulario del generador
    path('generar/',  views_rutinas.routine_generator_view, name='generate'),

    # 2. Historial de rutinas
    path('detalle/',  views_rutinas.routine_detail_view,    name='detail'),

    # APIs internas
    path('api/generar/',              views_rutinas.generate_routine_api,  name='api_generate'),
    path('api/save/',                 views_rutinas.save_routine_api,       name='api_save'),

    # FIX: nueva ruta para eliminar una rutina individual por ID
    path('api/eliminar/<str:routine_id>/', views_rutinas.delete_routine_api, name='api_delete'),
    
    # API para obtener rutina del día
    path('api/dia/', views_rutinas.get_routine_day_api, name='api_get_day'),
]