# backend/apps/documents/serializers.py
"""
Document API serializers
"""
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import Document, DocumentChunk


class DocumentSerializer(serializers.ModelSerializer):
    """Serializer for documents"""

    filename = serializers.SerializerMethodField()
    chunk_count = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            "id",
            "title",
            "filename",
            "document_type",
            "language",
            "product_line",
            "version",
            "description",
            "file_size",
            "page_count",
            "processed",
            "chunk_count",
            "created_at",
        ]
        read_only_fields = ["id", "file_size", "page_count", "processed", "created_at"]

    @extend_schema_field(OpenApiTypes.STR)
    def get_filename(self, obj):
        """Extract filename from file path"""
        return obj.get_filename()

    @extend_schema_field(OpenApiTypes.INT)
    def get_chunk_count(self, obj):
        return obj.chunks.count()


class DocumentChunkSerializer(serializers.ModelSerializer):
    """Serializer for document chunks"""

    document_title = serializers.ReadOnlyField(source="document.title")
    word_count = serializers.SerializerMethodField()

    class Meta:
        model = DocumentChunk
        fields = [
            "id",
            "document_title",
            "content",
            "page_number",
            "section_title",
            "chunk_index",
            "word_count",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    @extend_schema_field(OpenApiTypes.INT)
    def get_word_count(self, obj):
        """Calculate word count from content"""
        return len(obj.content.split()) if obj.content else 0
