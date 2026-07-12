import logging

from django.db import connection
from django.http import JsonResponse
from django.views.decorators.http import require_GET


logger = logging.getLogger("app.health")

@require_GET
def health(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        cursor.fetchone()
    logger.debug("health.ok database=ok")
    return JsonResponse({"status": "ok", "database": "ok"})
