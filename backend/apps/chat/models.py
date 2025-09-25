# backend/apps/chat/models.py
"""
Chat models for conversations and messages
"""
from django.db import models
from django.contrib.auth.models import User
import uuid


class Conversation(models.Model):
    """A conversation between user and AI"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    session_id = models.CharField(max_length=255, db_index=True, null=True, blank=True)
    title = models.CharField(max_length=255, blank=True)
    language = models.CharField(max_length=10, default='en')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"Conversation {self.id} - {self.title or 'Untitled'}"

    @staticmethod
    def get_or_create_for_session(session_id: str, language: str = 'en', title: str = ''):
        conv = Conversation.objects.filter(session_id=session_id).order_by('-updated_at').first()
        if conv:
            return conv, False
        return Conversation.objects.create(session_id=session_id, language=language, title=title[:255]), True


class Message(models.Model):
    """A message in a conversation"""
    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
        ('system', 'System'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(Conversation, related_name='messages', on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)  # Store citations, etc.
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.role}: {self.content[:50]}..."

    @property
    def citations(self):
        """Get citations from metadata"""
        return self.metadata.get('citations', [])

    def add_citation(self, document, page, section=None, text=""):
        """Add a citation to this message"""
        if 'citations' not in self.metadata:
            self.metadata['citations'] = []

        citation = {
            'document': document,
            'page': page,
            'section': section,
            'text': text
        }

        self.metadata['citations'].append(citation)
        self.save(update_fields=['metadata'])


class MessageFeedback(models.Model):
    """User feedback on assistant messages"""
    FEEDBACK_CHOICES = [
        ('helpful', 'Helpful'),
        ('not_helpful', 'Not Helpful'),
        ('step_helped', 'Step Helped'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(Message, related_name='feedback', on_delete=models.CASCADE)
    feedback_type = models.CharField(max_length=20, choices=FEEDBACK_CHOICES)
    is_positive = models.BooleanField()
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['message', 'feedback_type']

    def __str__(self):
        return f"Feedback on {self.message.id}: {self.feedback_type}"

