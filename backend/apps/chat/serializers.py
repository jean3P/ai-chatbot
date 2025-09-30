# backend/apps/chat/serializers.py

"""
Chat API serializers
"""
from rest_framework import serializers

from .models import Conversation, Message, MessageFeedback


class MessageSerializer(serializers.ModelSerializer):
    """Serializer for messages"""

    citations = serializers.ReadOnlyField()

    class Meta:
        model = Message
        fields = ["id", "role", "content", "citations", "created_at"]
        read_only_fields = ["id", "created_at"]


class ConversationSerializer(serializers.ModelSerializer):
    """Serializer for conversations"""

    messages = MessageSerializer(many=True, read_only=True)
    message_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            "id",
            "title",
            "language",
            "created_at",
            "updated_at",
            "messages",
            "message_count",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_message_count(self, obj):
        return obj.messages.count()


class ChatRequestSerializer(serializers.Serializer):
    """Serializer for chat requests"""

    message = serializers.CharField(max_length=2000)
    conversation_id = serializers.UUIDField(required=False)
    language = serializers.CharField(max_length=10, default="en")
    session_id = serializers.CharField(max_length=255, required=False)


class FeedbackSerializer(serializers.ModelSerializer):
    """Serializer for message feedback"""

    class Meta:
        model = MessageFeedback
        fields = [
            "id",
            "message",
            "feedback_type",
            "is_positive",
            "comment",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]
