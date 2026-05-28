"""
urls_perfil.py  –  BIO-FIT
Rutas para el módulo de perfil de usuario.

Incluir en urls_app.py:

    from apps.conexion import views_perfil

    urlpatterns = [
        ...
        path('perfil/',              views_perfil.perfil_page,                 name='perfil'),
        path('api/perfil/',          views_perfil.PerfilView.as_view(),        name='api_perfil'),
        path('api/perfil/gimnasio/', views_perfil.GimnasioVinculacionView.as_view(), name='api_gym_vinculacion'),
        path('api/gimnasios/',       views_perfil.GimnasioBuscadorView.as_view(),    name='api_gimnasios'),
    ]
"""

from django.urls import path
from . import views_perfil

urlpatterns = [
    # Página HTML
    path('',          views_perfil.perfil_page,                        name='perfil'),

    # API REST
    path('api/',      views_perfil.PerfilView.as_view(),               name='api_perfil'),
    path('api/gym/',  views_perfil.GimnasioVinculacionView.as_view(),  name='api_gym_vinculacion'),
]