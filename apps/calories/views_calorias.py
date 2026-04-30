from rest_framework.views import APIView
from rest_framework.response import Response
from .calculator import calcular_calorias_completas


class CaloriasView(APIView):
    def post(self, request):
        data = request.data

        resultado = calcular_calorias_completas(data)

        return Response(resultado)