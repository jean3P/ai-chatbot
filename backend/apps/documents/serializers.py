# backend/apps/documents/serializers.py
"""
Document API serializers
"""
from rest_framework import serializers
from .models import Document, DocumentChunk


class DocumentSerializer(serializers.ModelSerializer):
    """Serializer for documents"""
    filename = serializers.ReadOnlyField(source='get_filename')
    chunk_count = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            'id', 'title', 'filename', 'document_type', 'language',
            'product_line', 'version', 'description', 'file_size',
            'page_count', 'processed', 'chunk_count', 'created_at'
        ]
        read_only_fields = ['id', 'file_size', 'page_count', 'processed', 'created_at']

    def get_chunk_count(self, obj):
        return obj.chunks.count()


class DocumentChunkSerializer(serializers.ModelSerializer):
    """Serializer for document chunks"""
    document_title = serializers.ReadOnlyField(source='document.title')
    word_count = serializers.ReadOnlyField()

    class Meta:
        model = DocumentChunk
        fields = [
            'id', 'document_title', 'content', 'page_number',
            'section_title', 'chunk_index', 'word_count', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
