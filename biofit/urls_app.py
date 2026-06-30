from django.contrib import admin
from django.urls import path, include
from apps.users.views import (
    RegisterView, login_view, logout_view, auto_logout_view,
    login_page, registro_page, landing_page,
    recuperar_password_view, verificar_codigo_view, restablecer_password_view,
)
from apps.conexion import views_perfil
from apps.conexion.views_conexion import cambiar_password_page, confirmar_password_view
from apps.rutinas.views_rutinas import firebase_login_required
from django.shortcuts import render


def terminos_page(request):
    return render(request, 'terminos.html')


@firebase_login_required
def asistente_page(request):
    return render(request, 'asistente/chat.html')


urlpatterns = [
    path('admin/', admin.site.urls),
    path('',       landing_page, name='landing'),
    path('inicio/', landing_page, name='inicio'),
    path('login/',    login_page,    name='login'),
    path('registro/', registro_page, name='registro'),
    path('terminos/', terminos_page, name='terminos'),

    # ── Auth ──────────────────────────────────────────────────────────────
    path('api/register/', RegisterView.as_view(), name='api_register'),
    path('api/login/',    login_view,             name='api_login'),
    path('api/logout/',   logout_view,            name='api_logout'),
    path('auto-logout/',  auto_logout_view,        name='auto_logout'),

    # ── Recuperación de contraseña (flujo de código) ───────────────────────
    # Paso 1: solicitar código por email
    path('api/recuperar-password/',   recuperar_password_view,  name='api_recuperar_password'),
    # Paso 2: verificar el código de 6 dígitos
    path('api/verificar-codigo/',     verificar_codigo_view,    name='api_verificar_codigo'),
    # Paso 3: aplicar la nueva contraseña
    path('api/restablecer-password/', restablecer_password_view, name='api_restablecer_password'),

    # ── Cambio de contraseña obligatorio ──────────────────────────────────
    path('cambiar-password/',       cambiar_password_page,   name='cambiar_password'),
    path('api/confirmar-password/', confirmar_password_view, name='api_confirmar_password'),

    # ── Inventario (admin) ────────────────────────────────────────────────
    path('inventory/', include('apps.inventory.urls_inventario', namespace='inventory')),

    # ── Rutinas ───────────────────────────────────────────────────────────
    path('rutinas/', include('apps.rutinas.urls')),

    # ── Asistente ─────────────────────────────────────────────────────────
    path('asistente/', asistente_page, name='asistente'),

    # ── Perfil ────────────────────────────────────────────────────────────
    path('perfil/',     views_perfil.perfil_page,                       name='perfil'),
    path('api/perfil/', views_perfil.PerfilView.as_view(),              name='api_perfil'),

    path('api/perfil/gimnasio/', views_perfil.GimnasioVinculacionView.as_view(), name='api_gym_vinculacion'),

    path('api/gimnasios/', views_perfil.BuscarGimnasiosView.as_view(), name='api_buscar_gimnasios'),
]