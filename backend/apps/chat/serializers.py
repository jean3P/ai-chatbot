# apps/chat/serializers.py
"""
Chat API serializers with enhanced citation support
"""
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.documents.models import DocumentChunk

from .models import Conversation, Message, MessageFeedback


class MessageSerializer(serializers.ModelSerializer):
    """
    Serializer for messages with full citation metadata
    """

    citations = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ["id", "role", "content", "citations", "created_at", "metadata"]
        read_only_fields = ["id", "created_at"]

    @extend_schema_field(
        {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "document_title": {"type": "string"},
                    "page_number": {"type": "integer"},
                    "chunk_text": {"type": "string"},
                    "chunk_id": {"type": "string", "format": "uuid", "nullable": True},
                    "document_id": {
                        "type": "string",
                        "format": "uuid",
                        "nullable": True,
                    },
                    "relevance_score": {"type": "number", "format": "float"},
                    "section_title": {"type": "string"},
                },
            },
        }
    )
    def get_citations(self, obj):
        """
        Extract citations from message metadata and enrich with document data

        Returns structured citations for frontend display
        """
        # Only assistant messages have citations
        if obj.role != "assistant":
            return []

        # Get citation data from metadata
        citation_data = obj.metadata.get("citations", [])

        if not citation_data:
            return []

        # If citations already have all required fields, return as-is
        if citation_data and all(
            "document_title" in c and "chunk_id" in c for c in citation_data
        ):
            return citation_data

        # Convert old format to new format
        enriched_citations = []

        for citation in citation_data:
            # Check if this is old format (has 'document' instead of 'document_title')
            if "document" in citation and "document_title" not in citation:
                # Convert old format to new format
                enriched_citations.append(
                    {
                        "document_title": citation.get("document", "Unknown Source"),
                        "page_number": citation.get("page", 0),
                        "chunk_text": citation.get("text", "")[:500],
                        "chunk_id": None,
                        "document_id": None,
                        "relevance_score": citation.get("similarity_score", 0.0),
                        "section_title": citation.get("section", ""),
                    }
                )
                continue

            # Extract chunk ID
            chunk_id = citation.get("chunk_id")

            # If no chunk_id, try to enrich from metadata
            if not chunk_id:
                enriched_citations.append(citation)
                continue

            # Skip if this is a placeholder ID
            if chunk_id.startswith("citation_"):
                enriched_citations.append(citation)
                continue

            # If we have a real chunk_id, query the database
            try:
                from apps.documents.models import DocumentChunk

                chunk = DocumentChunk.objects.select_related("document").get(
                    id=chunk_id
                )

                enriched_citations.append(
                    {
                        "document_title": chunk.document.title,
                        "page_number": chunk.page_number or 0,
                        "chunk_text": chunk.content[:500],
                        "chunk_id": str(chunk.id),
                        "document_id": str(chunk.document.id),
                        "relevance_score": citation.get("relevance_score", 0.0),
                        "section_title": chunk.section_title or "",
                    }
                )
            except:
                # Chunk not found, return what we have
                enriched_citations.append(
                    {
                        "document_title": citation.get(
                            "document_title", "Unknown Source"
                        ),
                        "page_number": citation.get("page_number", 0),
                        "chunk_text": citation.get("chunk_text", "")[:500],
                        "chunk_id": chunk_id,
                        "document_id": None,
                        "relevance_score": citation.get("relevance_score", 0.0),
                        "section_title": citation.get("section_title", ""),
                    }
                )

        return enriched_citations


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

    @extend_schema_field(OpenApiTypes.INT)
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
