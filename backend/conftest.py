# backend/conftest.py

"""
Pytest configuration and fixtures.
"""
import pytest


@pytest.fixture(scope='session')
def django_db_setup():
    """Verify test database configuration."""
    from django.conf import settings

    db_config = settings.DATABASES['default']
    assert db_config['NAME'] == 'test_chatbot'
    assert db_config['PORT'] == '5433'
    assert settings.ENVIRONMENT == 'test'


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    """Automatically enable database access for all tests."""
    pass
