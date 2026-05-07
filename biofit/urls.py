from django.contrib import admin
from django.urls import path
# Importamos las vistas desde su ubicación en la app users
from apps.users.views import RegisterView, login_view, login_page, registro_page

urlpatterns = [
    # La ruta correcta es admin.site.urls
    path('admin/', admin.site.urls),

    # ── Páginas HTML ──────────────────────────────────────────
    path('login/', login_page, name='login-page'),
    path('registro/', registro_page, name='registro-page'),

    # ── API endpoints ─────────────────────────────────────────
    path('api/register/', RegisterView.as_view(), name='register'),
    path('api/login/', login_view, name='login'),
]