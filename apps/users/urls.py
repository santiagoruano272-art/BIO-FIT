# apps/users/urls.py — puedes simplificarlo o eliminarlo si no lo usas con include()
from django.urls import path
from .views import RegisterView, login_view

urlpatterns = [
    path('api/registro/', RegisterView.as_view()),
    path('api/login/', login_view),
]