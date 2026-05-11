from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
# Importamos las vistas de usuarios
from apps.users.views import RegisterView, login_view, login_page, registro_page, landing_page

urlpatterns = [
    path('admin/', admin.site.urls),

    # 1. Ruta raíz: Redirige al registro al abrir la web
    path('', lambda request: redirect('registro-page')),

    # 2. Páginas HTML de Usuarios
    path('login/', login_page, name='login-page'),
    path('registro/', registro_page, name='registro-page'),
    path('inicio/', landing_page, name='landing'), # Esta es la que carga landing.html

    # 3. APIs de Usuarios
    path('api/register/', RegisterView.as_view(), name='register'),
    path('api/login/', login_view, name='login'),

    # 4. RUTAS DE RUTINAS (Esto es lo que faltaba para corregir el error del botón)
    # Al poner namespace='routines', el botón {% url 'routines:generator' %} funcionará
    path('rutinas/', include('apps.rutinas.urls', namespace='routines')),
    ]  