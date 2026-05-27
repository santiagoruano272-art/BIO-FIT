from django.urls import path
from apps.inventory import views_inventario

app_name = 'inventory'

urlpatterns = [
    # Renderizados de plantillas HTML
    path('dashboard/',          views_inventario.admin_dashboard_view,    name='admin_dashboard'),
    path('registrar-gimnasio/', views_inventario.registrar_gimnasio_page, name='registrar_gimnasio_view'),

    # Endpoints funcionales de la API (JSON)
    path('api/gimnasios/',          views_inventario.GimnasiosPublicListAPI.as_view(), name='api_listar_gimnasios'),
    path('api/gimnasios/crear/',    views_inventario.GimnasioCreateAPI.as_view(),      name='api_crear_gimnasio'),
    path('api/gimnasios/contexto/', views_inventario.GimnasioContextoAPI.as_view(),    name='api_contexto_gimnasio'),
    path('api/equipos/',                        views_inventario.EquiposListCreateAPI.as_view(), name='api_equipos_list_create'),
    path('api/equipos/<str:equipo_id>/',        views_inventario.EquipoDetailAPI.as_view(),      name='api_equipo_detail'),
    path('api/equipos/<str:equipo_id>/eliminar/', views_inventario.EquipoDeleteAPI.as_view(),    name='api_equipo_delete'),
]