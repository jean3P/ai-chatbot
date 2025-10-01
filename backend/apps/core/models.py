# apps/core/models.py
"""
Core system models for monitoring and experimentation
"""
import uuid

from django.contrib.postgres.fields import ArrayField
from django.db import models


class Experiment(models.Model):
    """
    A/B testing configuration for RAG strategies

    Tracks different configurations and their performance for experimentation.
    """

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("active", "Active"),
        ("paused", "Paused"),
        ("completed", "Completed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")

    # Experiment configuration
    strategy_name = models.CharField(
        max_length=100, help_text="RAG strategy identifier (e.g., 'baseline', 'hybrid')"
    )
    config = models.JSONField(
        default=dict, help_text="Strategy configuration parameters"
    )

    # Traffic allocation
    traffic_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        help_text="Percentage of traffic allocated (0.00-100.00)",
    )

    # Targeting (optional)
    target_languages = ArrayField(
        models.CharField(max_length=10),
        blank=True,
        null=True,
        help_text="Limit experiment to specific languages (e.g., ['en', 'de'])",
    )
    target_document_types = ArrayField(
        models.CharField(max_length=50),
        blank=True,
        null=True,
        help_text="Limit to specific document types",
    )

    # Metrics tracking
    total_requests = models.IntegerField(default=0)
    successful_responses = models.IntegerField(default=0)
    avg_latency_ms = models.FloatField(null=True, blank=True)
    avg_cost_usd = models.FloatField(null=True, blank=True)

    # Timestamps
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "traffic_percentage"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.status})"

    @property
    def success_rate(self):
        """Calculate success rate percentage"""
        if self.total_requests == 0:
            return 0.0
        return (self.successful_responses / self.total_requests) * 100
