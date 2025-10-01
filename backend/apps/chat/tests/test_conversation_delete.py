# apps/chat/tests/test_conversation_delete.py
"""
Tests for conversation deletion endpoint
"""
import uuid

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.chat.models import Conversation, Message


@pytest.mark.django_db
class TestConversationDelete:
    """Test DELETE /api/chat/conversations/{id}/ endpoint"""

    def setup_method(self):
        """Set up test client and data"""
        self.client = APIClient()

        # Create test conversation
        self.conversation = Conversation.objects.create(
            session_id="test-session-123", title="Test Conversation", language="en"
        )

        # Create test messages
        self.messages = [
            Message.objects.create(
                conversation=self.conversation, role="user", content=f"User message {i}"
            )
            for i in range(3)
        ]

        Message.objects.create(
            conversation=self.conversation,
            role="assistant",
            content="Assistant response",
            metadata={"citations": []},
        )

    def test_delete_conversation_success(self):
        """Test successful conversation deletion"""
        url = reverse(
            "chat:conversation-detail", kwargs={"conversation_id": self.conversation.id}
        )

        response = self.client.delete(url, HTTP_X_SESSION_ID="test-session-123")

        assert response.status_code == 204
        assert not Conversation.objects.filter(id=self.conversation.id).exists()

    def test_delete_conversation_without_session(self):
        """Test deletion without session header (should succeed if no validation)"""
        url = reverse(
            "chat:conversation-delete", kwargs={"conversation_id": self.conversation.id}
        )

        response = self.client.delete(url)

        assert response.status_code == 204
        assert not Conversation.objects.filter(id=self.conversation.id).exists()

    def test_delete_conversation_wrong_session(self):
        """Test deletion with wrong session_id"""
        url = reverse(
            "chat:conversation-delete", kwargs={"conversation_id": self.conversation.id}
        )

        response = self.client.delete(url, HTTP_X_SESSION_ID="wrong-session-456")

        assert response.status_code == 403
        assert (
            response.data["error"]
            == "You do not have permission to delete this conversation"
        )

        # Conversation should still exist
        assert Conversation.objects.filter(id=self.conversation.id).exists()

    def test_delete_conversation_not_found(self):
        """Test deleting non-existent conversation"""
        fake_id = uuid.uuid4()
        url = reverse("chat:conversation-delete", kwargs={"conversation_id": fake_id})

        response = self.client.delete(url)

        assert response.status_code == 404

    def test_messages_cascade_deleted(self):
        """Test that messages are deleted when conversation is deleted"""
        conversation_id = self.conversation.id
        message_ids = [msg.id for msg in self.messages]

        url = reverse(
            "chat:conversation-delete", kwargs={"conversation_id": conversation_id}
        )

        # Verify messages exist before deletion
        assert Message.objects.filter(conversation_id=conversation_id).count() == 4

        # Delete conversation
        response = self.client.delete(url, HTTP_X_SESSION_ID="test-session-123")

        assert response.status_code == 204

        # Verify messages are deleted
        assert Message.objects.filter(id__in=message_ids).count() == 0
        assert Message.objects.filter(conversation_id=conversation_id).count() == 0

    def test_delete_with_session_in_query_param(self):
        """Test deletion with session_id in query parameter"""
        url = reverse(
            "chat:conversation-delete", kwargs={"conversation_id": self.conversation.id}
        )

        response = self.client.delete(f"{url}?session_id=test-session-123")

        assert response.status_code == 204
        assert not Conversation.objects.filter(id=self.conversation.id).exists()

    def test_delete_preserves_other_conversations(self):
        """Test that deleting one conversation doesn't affect others"""
        # Create another conversation
        other_conversation = Conversation.objects.create(
            session_id="other-session", title="Other Conversation", language="en"
        )
        Message.objects.create(
            conversation=other_conversation, role="user", content="Other message"
        )

        # Delete first conversation
        url = reverse(
            "chat:conversation-delete", kwargs={"conversation_id": self.conversation.id}
        )
        response = self.client.delete(url, HTTP_X_SESSION_ID="test-session-123")

        assert response.status_code == 204

        # Other conversation should still exist
        assert Conversation.objects.filter(id=other_conversation.id).exists()
        assert Message.objects.filter(conversation=other_conversation).count() == 1


@pytest.mark.django_db
class TestConversationDeleteEdgeCases:
    """Test edge cases for conversation deletion"""

    def setup_method(self):
        self.client = APIClient()

    def test_delete_with_invalid_uuid_format(self):
        """Test deletion with malformed UUID"""
        # Django will return 404 for invalid UUID format
        response = self.client.delete("/api/chat/conversations/not-a-uuid/delete/")

        assert response.status_code == 404

    def test_delete_with_special_characters_in_session(self):
        """Test deletion with special characters in session_id"""
        conversation = Conversation.objects.create(
            session_id="session-with-special!@#$%", title="Test", language="en"
        )

        url = reverse(
            "chat:conversation-delete", kwargs={"conversation_id": conversation.id}
        )
        response = self.client.delete(
            url, HTTP_X_SESSION_ID="session-with-special!@#$%"
        )

        assert response.status_code == 204
