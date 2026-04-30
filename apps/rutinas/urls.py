from django.urls import path
from django.http import JsonResponse

# vista temporal SOLO para probar que funciona
def test_rutinas(request):
    return JsonResponse({"msg": "rutinas funcionando"})

urlpatterns = [
    path('', test_rutinas),
]