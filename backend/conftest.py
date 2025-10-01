# backend/conftest.py

"""
Pytest configuration and fixtures.
"""
import pytest
from django.core.management import call_command


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    """Verify test database configuration and run migrations."""
    from django.conf import settings

    # Verify configuration
    db_config = settings.DATABASES["default"]
    assert db_config["NAME"] == "test_chatbot"
    assert db_config["PORT"] in [
        "5432",
        "5433",
    ], f"Unexpected port: {db_config['PORT']}"
    assert settings.ENVIRONMENT == "test"

    # Run migrations automatically
    with django_db_blocker.unblock():
        call_command("migrate", "--noinput", verbosity=0)


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    """Automatically enable database access for all tests."""
    pass
