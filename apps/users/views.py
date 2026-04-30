from rest_framework.views import APIView
from rest_framework.response import Response
from .auth import register_user


class RegisterView(APIView):
    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")

        uid = register_user(email, password)

        return Response({"uid": uid})