from django.urls import path
from .views import RegisterView, login_view, registro_page

urlpatterns = [
    # API
    path('registro/', RegisterView.as_view()),
    path('login/', login_view),

    # FRONTEND
    path('registro-page/', registro_page),
]