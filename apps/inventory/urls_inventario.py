from django.urls import path
from apps.inventory import views_inventario

app_name = 'inventory'

urlpatterns = [
    # ── Vista principal del gym_owner ────────────────────────────────────────
    path('dashboard/', views_inventario.dashboard_view, name='admin_dashboard'),

    # ── [ELIMINADO] Registro de gimnasios ─────────────────────────────────────
    # Las rutas 'api/gimnasios/crear/' y la vista 'registrar_gimnasio_view'
    # fueron eliminadas. Los gimnasios se crean directamente desde Firebase Console
    # o mediante un script interno de administración.

    # ── Gimnasios (solo lectura pública) ─────────────────────────────────────
    path('api/gimnasios/',          views_inventario.GimnasiosPublicListAPI.as_view(), name='api_listar_gimnasios'),
    path('api/gimnasios/contexto/', views_inventario.GimnasioContextoAPI.as_view(),    name='api_contexto_gimnasio'),

    # ── Gestión de equipos ────────────────────────────────────────────────────
    # ACCESO RESTRINGIDO: solo admin puede agregar/editar/eliminar.
    # La validación de rol ocurre en el backend (views_inventario.py).
    path('api/equipos/',                          views_inventario.EquiposListCreateAPI.as_view(), name='api_equipos_list_create'),
    path('api/equipos/<str:equipo_id>/',          views_inventario.EquipoDetailAPI.as_view(),      name='api_equipo_detail'),
    path('api/equipos/<str:equipo_id>/eliminar/', views_inventario.EquipoDeleteAPI.as_view(),      name='api_equipo_delete'),
]