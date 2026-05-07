from django.contrib import admin
from django.urls import path
from django.shortcuts import redirect  # ← agregar esto
from apps.users.views import RegisterView, login_view, login_page, registro_page
from django.urls import path, include

path('users/', include('apps.users.urls')),

urlpatterns = [
    path('admin/', admin.site.urls),

    # ── Ruta raíz → redirige al registro ──────────────────────
    path('', lambda request: redirect('registro-page')),  # ← agregar esto

    # ── Páginas HTML ──────────────────────────────────────────
    path('login/', login_page, name='login-page'),
    path('registro/', registro_page, name='registro-page'),

    # ── API endpoints ─────────────────────────────────────────
    path('api/register/', RegisterView.as_view(), name='register'),
    path('api/login/', login_view, name='login'),
]