# backend/apps/chat/admin.py
"""
Admin configuration for chat models
"""
from django.contrib import admin
from django.utils.html import format_html

from ..core.models import Experiment
from .models import AnswerLog, Conversation, Message, MessageFeedback


@admin.register(AnswerLog)
class AnswerLogAdmin(admin.ModelAdmin):
    list_display = [
        "created_at",
        "method",
        "llm_model",
        "total_latency_display",
        "tokens_display",
        "cost_display",
        "citations_count",
        "had_error",
    ]
    list_filter = [
        "method",
        "llm_model",
        "embedding_model",
        "had_error",
        "language",
        "created_at",
    ]
    search_fields = ["query", "error_message"]
    readonly_fields = [
        "id",
        "message",
        "experiment",
        "query",
        "method",
        "llm_model",
        "embedding_model",
        "created_at",
    ]

    fieldsets = (
        ("Request", {"fields": ("id", "message", "experiment", "query", "language")}),
        (
            "Method",
            {"fields": ("method", "strategy_config", "llm_model", "embedding_model")},
        ),
        (
            "Retrieval",
            {
                "fields": (
                    "chunks_retrieved",
                    "chunks_used",
                    "top_similarity_score",
                    "context_used",
                )
            },
        ),
        (
            "Tokens",
            {
                "fields": (
                    "prompt_tokens",
                    "completion_tokens",
                    "total_tokens",
                )
            },
        ),
        (
            "Performance",
            {
                "fields": (
                    "retrieval_latency_ms",
                    "generation_latency_ms",
                    "total_latency_ms",
                    "estimated_cost_usd",
                )
            },
        ),
        ("Quality", {"fields": ("citations_count", "sources_count")}),
        (
            "Error Tracking",
            {
                "fields": ("had_error", "error_type", "error_message"),
                "classes": ("collapse",),
            },
        ),
        ("Metadata", {"fields": ("metadata", "created_at"), "classes": ("collapse",)}),
    )

    def total_latency_display(self, obj):
        return f"{obj.total_latency_ms:.0f} ms"

    total_latency_display.short_description = "Latency"

    def tokens_display(self, obj):
        return f"{obj.total_tokens} ({obj.prompt_tokens}+{obj.completion_tokens})"

    tokens_display.short_description = "Tokens (prompt+completion)"

    def cost_display(self, obj):
        if obj.estimated_cost_usd:
            return f"${obj.estimated_cost_usd:.4f}"
        return "-"

    cost_display.short_description = "Cost"


@admin.register(Experiment)
class ExperimentAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "status",
        "strategy_name",
        "traffic_percentage",
        "total_requests",
        "success_rate_display",
        "avg_latency_display",
        "avg_cost_display",
        "created_at",
    ]
    list_filter = ["status", "strategy_name", "created_at"]
    search_fields = ["name", "description"]
    readonly_fields = [
        "id",
        "total_requests",
        "successful_responses",
        "avg_latency_ms",
        "avg_cost_usd",
        "created_at",
        "updated_at",
    ]

    fieldsets = (
        ("Basic Information", {"fields": ("id", "name", "description", "status")}),
        (
            "Configuration",
            {"fields": ("strategy_name", "config", "traffic_percentage")},
        ),
        (
            "Targeting",
            {
                "fields": ("target_languages", "target_document_types"),
                "classes": ("collapse",),
            },
        ),
        (
            "Metrics",
            {
                "fields": (
                    "total_requests",
                    "successful_responses",
                    "avg_latency_ms",
                    "avg_cost_usd",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("started_at", "ended_at", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    def success_rate_display(self, obj):
        rate = obj.success_rate
        color = "green" if rate >= 95 else "orange" if rate >= 80 else "red"
        return format_html('<span style="color: {};">{:.1f}%</span>', color, rate)

    success_rate_display.short_description = "Success Rate"

    def avg_latency_display(self, obj):
        if obj.avg_latency_ms:
            return f"{obj.avg_latency_ms:.0f} ms"
        return "-"

    avg_latency_display.short_description = "Avg Latency"

    def avg_cost_display(self, obj):
        if obj.avg_cost_usd:
            return f"${obj.avg_cost_usd:.4f}"
        return "-"

    avg_cost_display.short_description = "Avg Cost"


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "title",
        "language",
        "session_id",
        "created_at",
        "message_count",
    ]
    list_filter = ["language", "created_at"]
    search_fields = ["title", "session_id"]
    readonly_fields = ["id", "created_at", "updated_at"]

    def message_count(self, obj):
        return obj.messages.count()

    message_count.short_description = "Messages"


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ["id", "conversation", "role", "content_preview", "created_at"]
    list_filter = ["role", "created_at"]
    search_fields = ["content"]
    readonly_fields = ["id", "created_at"]

    def content_preview(self, obj):
        return obj.content[:100] + "..." if len(obj.content) > 100 else obj.content

    content_preview.short_description = "Content"


@admin.register(MessageFeedback)
class MessageFeedbackAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "message",
        "feedback_type",
        "is_positive",
        "rating",
        "created_at",
    ]
    list_filter = ["feedback_type", "is_positive", "rating", "created_at"]
    search_fields = ["comment", "user_query", "expected_answer"]
    readonly_fields = ["id", "created_at"]

    fieldsets = (
        ("Feedback", {"fields": ("message", "feedback_type", "is_positive", "rating")}),
        ("Details", {"fields": ("comment", "user_query", "expected_answer")}),
        ("Context", {"fields": ("session_id", "user_agent"), "classes": ("collapse",)}),
        ("Metadata", {"fields": ("id", "created_at"), "classes": ("collapse",)}),
    )
