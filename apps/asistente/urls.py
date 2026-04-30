from django.urls import path
from django.http import JsonResponse

def test_asistente(request):
    return JsonResponse({"msg": "asistente funcionando"})

urlpatterns = [
    path('', test_asistente),
]