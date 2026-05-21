from django.contrib import admin
from django.urls import path, include
from apps.users.views import RegisterView, login_view, login_page, registro_page, landing_page

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', landing_page, name='landing'),
    path('inicio/', landing_page, name='inicio'), 
    path('login/', login_page, name='login'),
    path('registro/', registro_page, name='registro'),
    path('api/register/', RegisterView.as_view(), name='api_register'),
    path('api/login/', login_view, name='api_login'),
    path('rutinas/', include('apps.rutinas.urls')),
    
    # 🚨 SOLUCIÓN: Agregamos el namespace='inventory' para que funcionen los tags {% url 'inventory:...' %}
    path('inventory/', include('apps.inventory.urls_inventario', namespace='inventory')),
]