# backend/config/settings/development.py
from .base import *

DEBUG = True

# Add debug toolbar for development
INSTALLED_APPS += ['django_extensions']

# Development-specific settings
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
