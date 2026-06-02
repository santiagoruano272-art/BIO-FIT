from django.contrib import admin
from django.urls import path, include
from apps.users.views import RegisterView, login_view, login_page, registro_page, landing_page
from apps.conexion import views_perfil
from apps.conexion.views_conexion import cambiar_password_page, confirmar_password_view


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', landing_page, name='landing'),
    path('inicio/', landing_page, name='inicio'),
    path('login/', login_page, name='login'),
    path('registro/', registro_page, name='registro'),

    # ── Auth ──────────────────────────────────────────────────────────────
    path('api/register/', RegisterView.as_view(), name='api_register'),
    path('api/login/',    login_view,             name='api_login'),

    # ── Cambio de contraseña obligatorio ─────────────────────────────────
    path('cambiar-password/',        cambiar_password_page,    name='cambiar_password'),
    path('api/confirmar-password/',  confirmar_password_view,  name='api_confirmar_password'),

    # ── Inventario (admin) ────────────────────────────────────────────────
    path('inventory/', include('apps.inventory.urls_inventario', namespace='inventory')),

    # ── Rutinas ───────────────────────────────────────────────────────────
    path('rutinas/', include('apps.rutinas.urls')),

    # ── Perfil ────────────────────────────────────────────────────────────
    path('perfil/',              views_perfil.perfil_page,                       name='perfil'),
    path('api/perfil/',          views_perfil.PerfilView.as_view(),              name='api_perfil'),
    path('api/perfil/gimnasio/', views_perfil.GimnasioVinculacionView.as_view(), name='api_gym_vinculacion'),
    path('api/gimnasios/',       views_perfil.GimnasioBuscadorView.as_view(),    name='api_gimnasios'),
]