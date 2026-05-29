from django.urls import path
from . import views_perfil

urlpatterns = [
    # Página HTML
    path('',                 views_perfil.perfil_page,                       name='perfil'),

    # APIs REST — usan sesión Django, sin Bearer token
    path('api/',             views_perfil.PerfilView.as_view(),              name='api_perfil'),
    path('api/gym/',         views_perfil.GimnasioVinculacionView.as_view(), name='api_gym_vinculacion'),

    # FIX: Buscador de gimnasios — ahora montado aquí directamente
    path('api/gimnasios/',   views_perfil.GimnasioBuscadorView.as_view(),    name='api_gimnasios_buscador'),
]