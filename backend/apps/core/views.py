# backend/apps/core/views.py
"""
Core application views including health checks
"""
import logging
import time

from django.db import connection
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

logger = logging.getLogger(__name__)


@extend_schema(
    tags=["Health"],
    summary="Database health check",
    description="Check if database connection is healthy and measure latency.",
    responses={
        200: OpenApiTypes.OBJECT,
        503: OpenApiTypes.OBJECT,
    },
)
@api_view(["GET"])
@permission_classes([AllowAny])
@never_cache
def database_health_check(request):
    """
    Database health check endpoint for load balancers and monitoring.

    Returns:
        200: Database is healthy
        503: Database is unreachable

    Response format:
        {"status": "healthy", "latency_ms": 12}
        {"status": "unhealthy", "error": "connection timeout"}
    """
    start_time = time.time()

    try:
        # Execute simple query with timeout
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()

        # Calculate latency
        latency_ms = round((time.time() - start_time) * 1000, 2)

        # Log warning if latency is high
        if latency_ms > 100:
            logger.warning(
                f"Database health check latency is high: {latency_ms}ms",
                extra={
                    "latency_ms": latency_ms,
                    "threshold_ms": 100,
                },
            )

        return JsonResponse(
            {
                "status": "healthy",
                "latency_ms": latency_ms,
                "database": connection.settings_dict.get("NAME"),
            },
            status=200,
        )

    except Exception as e:
        latency_ms = round((time.time() - start_time) * 1000, 2)

        logger.error(
            f"Database health check failed: {str(e)}",
            extra={
                "latency_ms": latency_ms,
                "error": str(e),
            },
            exc_info=True,
        )

        return JsonResponse(
            {
                "status": "unhealthy",
                "error": str(e),
                "latency_ms": latency_ms,
            },
            status=503,
        )


def api_root(request):
    """API root endpoint showing available endpoints"""
    return JsonResponse(
        {
            "message": "AI Chatbot API",
            "version": "1.0",
            "endpoints": {
                "health": "/api/health/db",
                "chat": "/api/chat/",
                "documents": "/api/documents/",
                "admin": "/admin/",
            },
        }
    )
