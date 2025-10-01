# config/settings/test.py
"""
Test environment settings.
"""
import os
from pathlib import Path

# Get BASE_DIR first
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Load .env.test BEFORE importing base (critical!)
from dotenv import load_dotenv

env_test_path = BASE_DIR / ".env.test"
if env_test_path.exists():
    load_dotenv(env_test_path, override=True)  # Force override

# NOW import base.py (it will use .env.test values)
from .base import *

# Force test environment
ENVIRONMENT = "test"

# Read from environment (now correctly from .env.test or CI)
DB_HOST = os.environ.get("DB_HOST", "127.0.0.1")
DB_PORT = os.environ.get("DB_PORT", "5433")
DB_NAME = os.environ.get("DB_NAME", "test_chatbot")
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "postgres")

# Test database configuration
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": DB_NAME,
        "USER": DB_USER,
        "PASSWORD": DB_PASSWORD,
        "HOST": DB_HOST,
        "PORT": DB_PORT,  # Now correctly uses .env.test value
        "CONN_MAX_AGE": 60,
        "ATOMIC_REQUESTS": True,
        "OPTIONS": {
            "connect_timeout": 10,
            "application_name": "swisson-chatbot-test",
        },
        "TEST": {
            "NAME": "test_chatbot",
        },
    }
}

# Redis
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": [("127.0.0.1", 6379)]},
    },
}

# Test settings
OPENROUTER_API_KEY = "test-key"
DEFAULT_EMBEDDING_MODEL = "test-model"
DEFAULT_LLM_MODEL = "test-model"

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
