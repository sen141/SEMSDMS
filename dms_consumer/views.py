from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    service = serializers.CharField()


class HealthView(APIView):
    @extend_schema(
        summary="Health check",
        responses={200: HealthResponseSerializer},
    )
    def get(self, request):
        return Response({"status": "ok", "service": "SEMSDMS"})