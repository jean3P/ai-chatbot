# backend/apps/chat/models.py
"""
Chat models for conversations and messages
"""
import uuid

from django.contrib.auth.models import User
from django.db import models


class Conversation(models.Model):
    """A conversation between user and AI"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    session_id = models.CharField(max_length=255, db_index=True, null=True, blank=True)
    title = models.CharField(max_length=255, blank=True)
    language = models.CharField(max_length=10, default="en")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"Conversation {self.id} - {self.title or 'Untitled'}"

    @staticmethod
    def get_or_create_for_session(
        session_id: str, language: str = "en", title: str = ""
    ):
        conv = (
            Conversation.objects.filter(session_id=session_id)
            .order_by("-updated_at")
            .first()
        )
        if conv:
            return conv, False
        return (
            Conversation.objects.create(
                session_id=session_id, language=language, title=title[:255]
            ),
            True,
        )


class Message(models.Model):
    """A message in a conversation"""

    ROLE_CHOICES = [
        ("user", "User"),
        ("assistant", "Assistant"),
        ("system", "System"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        Conversation, related_name="messages", on_delete=models.CASCADE
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)  # Store citations, etc.
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.role}: {self.content[:50]}..."

    @property
    def citations(self):
        """Get citations from metadata"""
        return self.metadata.get("citations", [])

    def add_citation(self, document, page, section=None, text=""):
        """Add a citation to this message"""
        if "citations" not in self.metadata:
            self.metadata["citations"] = []

        citation = {
            "document": document,
            "page": page,
            "section": section,
            "text": text,
        }

        self.metadata["citations"].append(citation)
        self.save(update_fields=["metadata"])


class MessageFeedback(models.Model):
    """User feedback on assistant messages"""

    FEEDBACK_CHOICES = [
        ("helpful", "Helpful"),
        ("not_helpful", "Not Helpful"),
        ("step_helped", "Step Helped"),
        ("incorrect", "Incorrect Information"),
        ("citation_missing", "Missing Citation"),
        ("citation_wrong", "Wrong Citation"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(
        Message, related_name="feedback", on_delete=models.CASCADE
    )
    feedback_type = models.CharField(max_length=20, choices=FEEDBACK_CHOICES)
    is_positive = models.BooleanField()

    # Enhanced feedback fields
    rating = models.IntegerField(
        null=True, blank=True, help_text="1-5 star rating (optional)"
    )
    comment = models.TextField(blank=True)

    # Context for feedback
    user_query = models.TextField(blank=True, help_text="What user was asking")
    expected_answer = models.TextField(blank=True, help_text="What user expected")

    # Metadata
    session_id = models.CharField(max_length=255, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = []  # Allow multiple feedback entries per message
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["feedback_type", "is_positive"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"Feedback on {self.message.id}: {self.feedback_type}"


class AnswerLog(models.Model):
    """
    Detailed logging for each RAG answer generation

    Tracks cost, latency, and performance metrics for monitoring and optimization.
    """

    METHOD_CHOICES = [
        ("baseline", "Baseline Strategy"),
        ("hybrid", "Hybrid Strategy"),
        ("rerank", "Rerank Strategy"),
        ("fallback", "Fallback Response"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Related entities
    message = models.OneToOneField(
        Message,
        on_delete=models.CASCADE,
        related_name="answer_log",
        help_text="Associated assistant message",
    )
    experiment = models.ForeignKey(
        "core.Experiment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="answer_logs",
        help_text="A/B test experiment if applicable",
    )

    # Query information
    query = models.TextField(help_text="User's original question")
    language = models.CharField(max_length=10, default="en")

    # RAG method used
    method = models.CharField(max_length=50, choices=METHOD_CHOICES)
    strategy_config = models.JSONField(
        default=dict, help_text="Strategy configuration used"
    )

    # Context retrieval metrics
    chunks_retrieved = models.IntegerField(default=0)
    chunks_used = models.IntegerField(default=0)
    top_similarity_score = models.FloatField(null=True, blank=True)
    context_used = models.BooleanField(default=True)

    # Generation metrics
    llm_model = models.CharField(max_length=100)
    embedding_model = models.CharField(max_length=100)
    prompt_tokens = models.IntegerField(default=0)
    completion_tokens = models.IntegerField(default=0)
    total_tokens = models.IntegerField(default=0)

    # Performance metrics
    retrieval_latency_ms = models.FloatField(null=True, blank=True)
    generation_latency_ms = models.FloatField(null=True, blank=True)
    total_latency_ms = models.FloatField(help_text="End-to-end latency")

    # Cost tracking
    estimated_cost_usd = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="Estimated API cost in USD",
    )

    # Quality indicators
    citations_count = models.IntegerField(default=0)
    sources_count = models.IntegerField(default=0)

    # Error tracking
    had_error = models.BooleanField(default=False)
    error_type = models.CharField(max_length=100, blank=True)
    error_message = models.TextField(blank=True)

    # Additional metadata
    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["method", "created_at"]),
            models.Index(fields=["llm_model", "created_at"]),
            models.Index(fields=["had_error"]),
            models.Index(fields=["experiment", "created_at"]),
        ]

    def __str__(self):
        return f"Log for {self.message_id} ({self.method})"

    @property
    def tokens_per_second(self):
        """Calculate throughput"""
        if self.generation_latency_ms and self.generation_latency_ms > 0:
            return (self.completion_tokens / self.generation_latency_ms) * 1000
        return 0.0
