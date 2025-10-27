# backend/apps/documents/urls.py
"""
Documents app URLs
"""
from django.urls import path

from . import views

app_name = "documents"

urlpatterns = [
    # Specific routes BEFORE generic ones
    path("search/", views.search_chunks, name="search-chunks"),
    path("<uuid:document_id>/chunks/", views.document_chunks, name="document-chunks"),
    path("<uuid:document_id>/", views.document_detail, name="document-detail"),
    # Generic list last
    path("", views.document_list, name="document-list"),
]
