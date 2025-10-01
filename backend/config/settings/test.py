# config/settings/test.py
"""
Test environment settings.

This file is used exclusively for running tests.
"""

from .base import *

# Force test environment
ENVIRONMENT = "test"

# Get port from environment BEFORE loading dotenv
# This ensures CI can override the port
DB_PORT = os.environ.get("DB_PORT", "5433")  # Read early

# Override with test-specific environment variables
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Load .env.test explicitly
from dotenv import load_dotenv

env_test_path = BASE_DIR / ".env.test"
if env_test_path.exists():
    load_dotenv(env_test_path, override=False)

# Test database configuration
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DB_NAME", "test_chatbot"),
        "USER": os.environ.get("DB_USER", "postgres"),
        "PASSWORD": os.environ.get("DB_PASSWORD", "postgres"),
        "HOST": os.environ.get("DB_HOST", "127.0.0.1"),
        "PORT": DB_PORT,  # Use the early-captured port
        "CONN_MAX_AGE": 60,
        "ATOMIC_REQUESTS": True,
        "OPTIONS": {
            "connect_timeout": 10,
            "application_name": "swisson-chatbot-test",
            "options": "-c search_path=public",
        },
        "TEST": {
            "NAME": "test_chatbot",
        },
    }
}

# Redis for tests
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [("127.0.0.1", 6379)],
        },
    },
}

# Disable external API calls in tests
OPENROUTER_API_KEY = "test-key"
DEFAULT_EMBEDDING_MODEL = "test-model"
DEFAULT_LLM_MODEL = "test-model"

# Speed up password hashing in tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Disable migrations for faster tests (optional)
# class DisableMigrations:
#     def __contains__(self, item):
#         return True
#     def __getitem__(self, item):
#         return None
# MIGRATION_MODULES = DisableMigrations()
