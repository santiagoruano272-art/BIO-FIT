from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),

    # USERS
    path('api/users/', include('apps.users.urls')),
]