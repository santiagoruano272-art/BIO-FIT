"""
urls_perfil.py  –  BIO-FIT

NOTA: En urls_app.py las rutas de perfil están montadas directamente
(no con include), por lo que este archivo es un módulo de referencia
disponible para si se quiere migrar a include('apps.conexion.urls_perfil').

Si se usa include(), agregar en urls_app.py:
    path('perfil/', include('apps.conexion.urls_perfil')),
y eliminar las rutas individuales de perfil en urls_app.py.
"""
from django.urls import path
from . import views_perfil

urlpatterns = [
    # Página HTML
    path('',              views_perfil.perfil_page,                       name='perfil'),

    # APIs REST — usan sesión Django, sin Bearer token
    path('api/',          views_perfil.PerfilView.as_view(),              name='api_perfil'),
    path('api/gimnasio/', views_perfil.GimnasioVinculacionView.as_view(), name='api_gym_vinculacion'),

    # FIX: nombre del endpoint alineado con urls_app.py ('api/gimnasios/' no 'api/gym/')
    path('api/gimnasios/', views_perfil.GimnasioBuscadorView.as_view(),   name='api_gimnasios_buscador'),
]