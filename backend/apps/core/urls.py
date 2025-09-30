# backend/apps/core/urls.py

"""
Core application URLs
"""
from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.api_root, name="api_root"),
    path("health/db", views.database_health_check, name="database_health"),
]
