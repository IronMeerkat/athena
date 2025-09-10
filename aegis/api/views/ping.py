from django.http import HttpRequest
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView


class PingView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request: HttpRequest) -> Response:  # type: ignore[override]
        _ = request
        return Response({"status": "ok"})
