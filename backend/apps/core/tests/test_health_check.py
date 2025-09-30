# backend/apps/core/tests/test_health_check.py
"""
Tests for health check endpoints
"""
import itertools
from unittest.mock import MagicMock, patch

import pytest
from django.db import connection
from django.test import Client
from django.urls import reverse


@pytest.mark.django_db
class TestDatabaseHealthCheck:
    """Test database health check endpoint"""

    def test_health_check_success(self):
        """Test successful health check"""
        client = Client()
        response = client.get(reverse("core:database_health"))

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "latency_ms" in data
        assert isinstance(data["latency_ms"], (int, float))
        assert data["latency_ms"] >= 0

    def test_health_check_includes_database_name(self):
        """Test response includes database name"""
        client = Client()
        response = client.get(reverse("core:database_health"))

        data = response.json()
        assert "database" in data
        assert data["database"] is not None

    def test_health_check_database_failure(self):
        """Test health check when database is unavailable"""
        client = Client()

        # Conditional side effect: only raise on SELECT 1, not on SAVEPOINT/RELEASE
        def execute_side_effect(sql, *args, **kwargs):
            if "SELECT 1" in str(sql):
                raise Exception("Database connection failed")
            return MagicMock()

        with patch.object(connection, "cursor") as mock_cursor:
            mock_cursor_instance = MagicMock()
            mock_cursor_instance.__enter__ = MagicMock(
                return_value=mock_cursor_instance
            )
            mock_cursor_instance.__exit__ = MagicMock(return_value=False)
            mock_cursor_instance.execute.side_effect = execute_side_effect
            mock_cursor_instance.fetchone.return_value = None
            mock_cursor.return_value = mock_cursor_instance

            response = client.get(reverse("core:database_health"))

        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert "error" in data
        assert "Database connection failed" in data["error"]

    def test_health_check_high_latency_warning(self, caplog):
        """Test warning is logged for high latency"""
        import logging

        client = Client()

        # Use itertools.chain to provide non-exhausting time values
        with patch("apps.core.views.time.time") as mock_time:
            # First two calls return 0 and 0.15, then repeat 0.15 for logging
            mock_time.side_effect = itertools.chain([0, 0.15], itertools.repeat(0.15))

            with caplog.at_level(logging.WARNING):
                response = client.get(reverse("core:database_health"))

        assert response.status_code == 200
        data = response.json()
        assert data["latency_ms"] == 150.0

        # Check warning was logged
        assert any(
            "Database health check latency is high" in record.message
            for record in caplog.records
        )

    def test_health_check_no_cache(self):
        """Test response has no-cache headers"""
        client = Client()
        response = client.get(reverse("core:database_health"))

        cache_control = response.get("Cache-Control", "")
        assert (
            "no-cache" in cache_control.lower()
            or "no-store" in cache_control.lower()
            or "max-age=0" in cache_control.lower()
        )

    def test_health_check_only_get_method(self):
        """Test endpoint only accepts GET requests"""
        client = Client()

        # POST should fail
        response = client.post(reverse("core:database_health"))
        assert response.status_code == 405

        # PUT should fail
        response = client.put(reverse("core:database_health"))
        assert response.status_code == 405

        # DELETE should fail
        response = client.delete(reverse("core:database_health"))
        assert response.status_code == 405
