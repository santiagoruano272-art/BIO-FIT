from django.urls import path
from apps.inventory import views_inventario

# 🚨 CRUCIAL: Vincula internamente el nombre de la aplicación para el ruteo dinámico de Django
app_name = 'inventory'

urlpatterns = [
    # Renderizados de plantillas HTML
    path('dashboard/', views_inventario.admin_dashboard_view, name='admin_dashboard'),
    path('registrar-gimnasio/', views_inventario.registrar_gimnasio_page, name='registrar_gimnasio_view'),
    
    # Endpoints funcionales de la API (JSON)
    path('api/gimnasios/', views_inventario.GimnasioCreateAPI.as_view(), name='api_crear_gimnasio'),
    path('api/equipos/', views_inventario.EquiposListCreateAPI.as_view(), name='api_equipos_list_create'),
    path('api/equipos/<str:equipo_id>/', views_inventario.EquipoDetailAPI.as_view(), name='api_equipo_detail'),
    path('api/equipos/<str:equipo_id>/eliminar/', views_inventario.EquipoDeleteAPI.as_view(), name='api_equipo_delete'),
]