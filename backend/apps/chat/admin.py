# backend/apps/chat/admin.py
"""
Admin configuration for chat models
"""
from django.contrib import admin

from .models import Conversation, Message, MessageFeedback


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "title",
        "language",
        "session_id",
        "created_at",
        "message_count",
    ]
    list_filter = ["language", "created_at"]
    search_fields = ["title", "session_id"]
    readonly_fields = ["id", "created_at", "updated_at"]

    def message_count(self, obj):
        return obj.messages.count()

    message_count.short_description = "Messages"


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ["id", "conversation", "role", "content_preview", "created_at"]
    list_filter = ["role", "created_at"]
    search_fields = ["content"]
    readonly_fields = ["id", "created_at"]

    def content_preview(self, obj):
        return obj.content[:100] + "..." if len(obj.content) > 100 else obj.content

    content_preview.short_description = "Content"


@admin.register(MessageFeedback)
class MessageFeedbackAdmin(admin.ModelAdmin):
    list_display = ["id", "message", "feedback_type", "is_positive", "created_at"]
    list_filter = ["feedback_type", "is_positive", "created_at"]
    readonly_fields = ["id", "created_at"]
