from django.urls import path
from . import views_inventario

app_name = 'inventory'

urlpatterns = [
    # Interfaz Web
    path('dashboard/', views_inventario.inventory_dashboard_view, name='dashboard'),
    
    # API endpoints (AJAX/Fetch)
    path('api/crear/', views_inventario.create_equipment_api, name='api_create'),
    path('api/editar/<str:equip_id>/', views_inventario.update_equipment_api, name='api_update'),
    path('api/eliminar/<str:equip_id>/', views_inventario.delete_equipment_api, name='api_delete'),
]