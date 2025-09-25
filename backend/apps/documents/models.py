# backend/apps/documents/models.py
"""
Document models for PDF processing and storage
"""
from django.db import models
import uuid
import os


class Document(models.Model):
    """A document (PDF, text file, etc.)"""
    DOCUMENT_TYPES = [
        ('manual', 'Manual'),
        ('datasheet', 'Datasheet'),
        ('firmware_notes', 'Firmware Notes'),
        ('quick_start', 'Quick Start Guide'),
        ('other', 'Other'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    file_path = models.FileField(upload_to='documents/')
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES, default='other')
    language = models.CharField(max_length=10, default='en')
    product_line = models.CharField(max_length=100, blank=True)
    version = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True)
    file_size = models.PositiveIntegerField(default=0)
    page_count = models.PositiveIntegerField(default=0)
    processed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.document_type})"

    def get_filename(self):
        """Get the original filename"""
        if self.file_path:
            return os.path.basename(self.file_path.name)
        return "Unknown"


class DocumentChunk(models.Model):
    """A chunk of text from a document for RAG"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(Document, related_name='chunks', on_delete=models.CASCADE)
    content = models.TextField()
    page_number = models.PositiveIntegerField(null=True, blank=True)
    section_title = models.CharField(max_length=255, blank=True)
    chunk_index = models.PositiveIntegerField()
    embedding = models.JSONField(null=True, blank=True)  # Store embedding vector
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['document', 'chunk_index']
        unique_together = ['document', 'chunk_index']

    def __str__(self):
        return f"Chunk {self.chunk_index} of {self.document.title}"

    @property
    def word_count(self):
        """Get word count of the chunk"""
        return len(self.content.split())
