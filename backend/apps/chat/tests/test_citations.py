# apps/chat/tests/test_citations.py
"""
Tests for citation functionality in chat responses
"""
import uuid

import pytest
from django.test import TestCase
from rest_framework.test import APIClient

from apps.chat.models import Conversation, Message
from apps.chat.serializers import MessageSerializer
from apps.documents.models import Document, DocumentChunk


@pytest.mark.django_db
class TestCitationSerialization(TestCase):
    """Test citation serialization in message responses"""

    def setUp(self):
        """Set up test data"""
        # Create test document
        self.document = Document.objects.create(
            title="DMX Splitter XPD-42 Manual",
            document_type="manual",
            language="en",
            processed=True,
        )

        # Create test chunks
        self.chunk1 = DocumentChunk.objects.create(
            document=self.document,
            content="Connect the DMX input cable to port 1. Ensure proper termination.",
            page_number=12,
            section_title="Installation",
            chunk_index=0,
            embedding=[0.1] * 384,  # Mock embedding
        )

        self.chunk2 = DocumentChunk.objects.create(
            document=self.document,
            content="The XPD-42 supports RDM protocol for remote configuration.",
            page_number=15,
            section_title="Features",
            chunk_index=1,
            embedding=[0.2] * 384,
        )

        # Create conversation
        self.conversation = Conversation.objects.create(
            session_id="test-session", language="en", title="Test Conversation"
        )

    def test_message_with_citations_serialization(self):
        """Test that message with citations serializes correctly"""
        # Create message with citation metadata
        message = Message.objects.create(
            conversation=self.conversation,
            role="assistant",
            content="According to the XPD-42 Manual, Page 12, connect the DMX input cable to port 1.",
            metadata={
                "citations": [
                    {
                        "document_title": self.document.title,
                        "page_number": 12,
                        "chunk_text": self.chunk1.content[:500],
                        "chunk_id": str(self.chunk1.id),
                        "document_id": str(self.document.id),
                        "relevance_score": 0.89,
                    }
                ]
            },
        )

        # Serialize
        serializer = MessageSerializer(message)
        data = serializer.data

        # Verify citations are present
        assert "citations" in data
        assert len(data["citations"]) == 1

        # Verify citation structure
        citation = data["citations"][0]
        assert citation["document_title"] == "DMX Splitter XPD-42 Manual"
        assert citation["page_number"] == 12
        assert citation["chunk_id"] == str(self.chunk1.id)
        assert citation["document_id"] == str(self.document.id)
        assert "chunk_text" in citation
        assert "relevance_score" in citation

    def test_message_with_old_format_citations(self):
        """Test backward compatibility with old citation format"""
        # Create message with old format citations (missing chunk_id/document_id)
        message = Message.objects.create(
            conversation=self.conversation,
            role="assistant",
            content="Test response",
            metadata={
                "citations": [
                    {
                        "id": "citation_0",
                        "document": "Old Format Doc",
                        "page": 5,
                        "text": "Old format text...",
                        "similarity_score": 0.75,
                    }
                ]
            },
        )

        # Serialize
        serializer = MessageSerializer(message)
        data = serializer.data

        # Should still return citations (converted to new format)
        assert "citations" in data
        assert len(data["citations"]) == 1
        citation = data["citations"][0]

        # FIXED: Check for 'document' field since serializer handles old format
        assert (
            citation["document_title"] == "Old Format Doc"
        )  # ← Changed from checking 'document_title'
        assert citation["page_number"] == 5

    def test_message_with_chunk_enrichment(self):
        """Test that serializer enriches citations by querying chunks"""
        # Create message with minimal citation data (only chunk_id)
        message = Message.objects.create(
            conversation=self.conversation,
            role="assistant",
            content="Test response",
            metadata={
                "citations": [
                    {"chunk_id": str(self.chunk1.id), "relevance_score": 0.85}
                ]
            },
        )

        # Serialize
        serializer = MessageSerializer(message)
        data = serializer.data

        # Verify chunk was queried and enriched
        assert len(data["citations"]) == 1
        citation = data["citations"][0]
        assert citation["document_title"] == self.document.title
        assert citation["page_number"] == 12
        assert citation["chunk_text"] == self.chunk1.content[:500]
        assert citation["document_id"] == str(self.document.id)

    def test_message_without_citations(self):
        """Test that user messages return empty citations"""
        message = Message.objects.create(
            conversation=self.conversation,
            role="user",
            content="How do I install the splitter?",
        )

        serializer = MessageSerializer(message)
        data = serializer.data

        assert data["citations"] == []

    def test_assistant_message_no_citations(self):
        """Test assistant message with no citations"""
        message = Message.objects.create(
            conversation=self.conversation,
            role="assistant",
            content="I don't have specific information about that.",
        )

        serializer = MessageSerializer(message)
        data = serializer.data

        assert data["citations"] == []

    def test_citation_with_deleted_chunk(self):
        """Test handling of citation referencing deleted chunk"""
        deleted_chunk_id = uuid.uuid4()

        message = Message.objects.create(
            conversation=self.conversation,
            role="assistant",
            content="Test response",
            metadata={
                "citations": [
                    {
                        "chunk_id": str(deleted_chunk_id),
                        "document": "Deleted Doc",
                        "page": 10,
                        "text": "This chunk was deleted",
                        "relevance_score": 0.8,
                    }
                ]
            },
        )

        serializer = MessageSerializer(message)
        data = serializer.data

        # Should handle gracefully
        assert len(data["citations"]) == 1
        citation = data["citations"][0]
        assert citation["document_title"] == "Deleted Doc"
        assert citation["document_id"] is None

    def test_chunk_text_truncation(self):
        """Test that long chunk text is truncated to 500 chars"""
        long_content = "A" * 1000
        chunk = DocumentChunk.objects.create(
            document=self.document,
            content=long_content,
            page_number=20,
            chunk_index=2,
            embedding=[0.3] * 384,
        )

        message = Message.objects.create(
            conversation=self.conversation,
            role="assistant",
            content="Test",
            metadata={
                "citations": [{"chunk_id": str(chunk.id), "relevance_score": 0.9}]
            },
        )

        serializer = MessageSerializer(message)
        data = serializer.data

        citation = data["citations"][0]
        assert len(citation["chunk_text"]) == 500


@pytest.mark.django_db
class TestCitationAPIResponse(TestCase):
    """Test citation data in API responses"""

    def setUp(self):
        """Set up test client and data"""
        self.client = APIClient()

        # Create test document and chunk
        self.document = Document.objects.create(
            title="Test Manual", document_type="manual", processed=True
        )

        self.chunk = DocumentChunk.objects.create(
            document=self.document,
            content="Test installation instructions",
            page_number=5,
            chunk_index=0,  # ← ADD THIS LINE
            embedding=[0.1] * 384,
        )

    def test_chat_response_includes_citations(self):
        """Test that chat API returns citations in response"""
        # This test would require mocking RAG pipeline
        # For now, test the serialization directly

        conversation = Conversation.objects.create(session_id="api-test", language="en")

        message = Message.objects.create(
            conversation=conversation,
            role="assistant",
            content="Installation instructions are on page 5",
            metadata={
                "citations": [{"chunk_id": str(self.chunk.id), "relevance_score": 0.88}]
            },
        )

        # Get conversation detail
        response = self.client.get(f"/api/chat/conversations/{conversation.id}/")

        assert response.status_code == 200
        assert "messages" in response.data

        # Find assistant message
        assistant_msg = next(
            m for m in response.data["messages"] if m["role"] == "assistant"
        )

        # Verify citations
        assert "citations" in assistant_msg
        assert len(assistant_msg["citations"]) > 0

        citation = assistant_msg["citations"][0]
        assert citation["document_title"] == "Test Manual"
        assert citation["page_number"] == 5
        assert citation["chunk_id"] == str(self.chunk.id)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
