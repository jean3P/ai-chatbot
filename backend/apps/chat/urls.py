# backend/apps/chat/urls.py

"""
Chat app URLs with RAG endpoints
"""
from django.urls import path

from . import views

app_name = "chat"

urlpatterns = [
    # Original chat endpoints
    path("", views.chat, name="chat"),
    path("conversations/", views.conversation_list, name="conversation-list"),
    # DELETE must come BEFORE generic detail route
    path(
        "conversations/<uuid:conversation_id>/delete/",
        views.conversation_delete,
        name="conversation-delete",
    ),
    path(
        "conversations/<uuid:conversation_id>/",
        views.conversation_detail,
        name="conversation-detail",
    ),
    path("feedback/", views.feedback, name="feedback"),
    # New RAG endpoints
    path("search/", views.search_documents, name="search-documents"),
    path("stats/", views.rag_stats, name="rag-stats"),
]
