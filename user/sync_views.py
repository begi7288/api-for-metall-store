import json
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser, JSONParser, FormParser
from django.http import HttpResponse

from user.sync_service import export_full_backup, import_full_backup, get_sync_summary

logger = logging.getLogger(__name__)

class SyncPullAPIView(APIView):
    """
    API endpoint to export / download complete system database backup from Cloud Server.
    Used by new local computers to restore all data after computer crash / setup.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        biznes = None
        if hasattr(request.user, 'xodim') and request.user.xodim:
            biznes = request.user.xodim.biznes

        backup_data = export_full_backup(biznes=biznes if not request.user.is_superuser else None)

        if request.query_params.get('download') == 'true':
            response = HttpResponse(
                json.dumps(backup_data, indent=2, ensure_ascii=False),
                content_type='application/json'
            )
            response['Content-Disposition'] = 'attachment; filename="temirdokon_backup.json"'
            return response

        return Response(backup_data, status=status.HTTP_200_OK)


class SyncPushAPIView(APIView):
    """
    API endpoint for local node to push local data changes/backup to Cloud Server.
    Cloud server receives JSON payload and merges/saves records.
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def post(self, request, *args, **kwargs):
        payload = request.data
        if 'file' in request.FILES:
            file_obj = request.FILES['file']
            payload = json.loads(file_obj.read().decode('utf-8'))
        elif isinstance(payload, str):
            payload = json.loads(payload)

        if not payload or 'models' not in payload:
            return Response(
                {"success": False, "error": "Noto'g me'yoriy backup JSON formati. 'models' maydoni bo'lishi shart."},
                status=status.HTTP_400_BAD_REQUEST
            )

        result = import_full_backup(payload, clear_existing=False)
        return Response(result, status=status.HTTP_200_OK)


class SyncRestoreAPIView(APIView):
    """
    API endpoint on local computer to perform full system restore from backup JSON payload.
    Replaces / populates local SQLite database.
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def post(self, request, *args, **kwargs):
        payload = request.data
        if 'file' in request.FILES:
            file_obj = request.FILES['file']
            payload = json.loads(file_obj.read().decode('utf-8'))
        elif isinstance(payload, str):
            payload = json.loads(payload)

        clear_db = str(request.query_params.get('clear', 'false')).lower() in ('true', '1', 'yes')

        if not payload or 'models' not in payload:
            return Response(
                {"success": False, "error": "Noto'g me'yoriy backup JSON formati. 'models' maydoni bo'lishi shart."},
                status=status.HTTP_400_BAD_REQUEST
            )

        result = import_full_backup(payload, clear_existing=clear_db)
        return Response({
            "success": True,
            "message": "Barcha ma'lumotlar muvaffaqiyatli lokal SQLite ga tiklandi!",
            **result
        }, status=status.HTTP_200_OK)


class SyncStatusAPIView(APIView):
    """
    API endpoint to check total record counts and sync status.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        summary = get_sync_summary()
        return Response({
            "success": True,
            "status": "online",
            "summary": summary
        }, status=status.HTTP_200_OK)
