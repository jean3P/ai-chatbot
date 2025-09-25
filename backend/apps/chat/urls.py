# backend/apps/chat/urls.py
"""
Chat app URLs
"""
from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    path('', views.chat, name='chat'),
    path('conversations/', views.conversation_list, name='conversation-list'),
    path('conversations/<uuid:conversation_id>/', views.conversation_detail, name='conversation-detail'),
    path('feedback/', views.feedback, name='feedback'),
]
