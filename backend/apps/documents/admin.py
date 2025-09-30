# backend/apps/documents/admin.py
"""
Admin configuration for document models
"""
from django.contrib import admin

from .models import Document, DocumentChunk


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "document_type",
        "language",
        "product_line",
        "processed",
        "chunk_count",
        "created_at",
    ]
    list_filter = ["document_type", "language", "processed", "created_at"]
    search_fields = ["title", "product_line", "description"]
    readonly_fields = ["id", "file_size", "page_count", "created_at", "updated_at"]

    def chunk_count(self, obj):
        return obj.chunks.count()

    chunk_count.short_description = "Chunks"


@admin.register(DocumentChunk)
class DocumentChunkAdmin(admin.ModelAdmin):
    list_display = [
        "document",
        "chunk_index",
        "page_number",
        "section_title",
        "word_count",
        "created_at",
    ]
    list_filter = ["document__document_type", "page_number", "created_at"]
    search_fields = ["content", "section_title"]
    readonly_fields = ["id", "word_count", "created_at"]

    def word_count(self, obj):
        return obj.word_count

    word_count.short_description = "Words"
