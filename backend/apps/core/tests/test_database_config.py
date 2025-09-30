"""
Tests for database configuration
"""

import pytest
from django.conf import settings
from django.db import connection


@pytest.mark.django_db
class TestDatabaseConfiguration:
    """Test database is configured correctly for tests"""

    def test_database_connection(self):
        """Verify test database is accessible"""
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            assert result[0] == 1

    def test_using_test_database(self):
        """Verify we're using the test database"""
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_database()")
            db_name = cursor.fetchone()[0]
            assert db_name == "test_chatbot", f"Expected test_chatbot, got {db_name}"

    def test_database_is_postgresql(self):
        """Verify we're using PostgreSQL, not SQLite"""
        assert (
            connection.vendor == "postgresql"
        ), f"Expected postgresql, got {connection.vendor}"

    def test_database_port(self):
        """Verify using test database port (5433 local, 5432 CI)"""
        db_settings = settings.DATABASES["default"]
        assert db_settings["PORT"] in ["5432", "5433"], (
            f"Expected port 5432 (CI) or 5433 (local), got {db_settings['PORT']}"
        )

    def test_pgvector_available(self):
        """Verify pgvector extension is available"""
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT EXISTS(
                    SELECT 1 FROM pg_extension WHERE extname = 'vector'
                )
            """
            )
            result = cursor.fetchone()[0]
            assert result is True, "pgvector extension not found"

    def test_environment_is_test(self):
        """Verify ENVIRONMENT is set to 'test'"""
        assert (
            settings.ENVIRONMENT == "test"
        ), f"Expected test, got {settings.ENVIRONMENT}"


@pytest.mark.django_db
class TestDatabaseOperations:
    """Test basic database operations"""

    def test_create_user(self):
        """Test creating a Django user"""
        from django.contrib.auth.models import User

        user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.check_password("testpass123")

    def test_database_isolation(self):
        """Test that database is clean for each test"""
        from django.contrib.auth.models import User

        # Should be no users at start of test
        user_count = User.objects.count()
        assert user_count == 0, f"Expected 0 users, got {user_count}"


@pytest.mark.unit
def test_simple_assertion():
    """Simple test without database"""
    assert 1 + 1 == 2
