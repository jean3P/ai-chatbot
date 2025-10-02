# apps/core/admin.py
"""
Admin configuration for core models
"""
from django.contrib import admin
from django.utils.html import format_html

from .models import Experiment, FeatureFlag


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


@admin.register(FeatureFlag)
class FeatureFlagAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "status_badge",
        "rollout_display",
        "description_preview",
        "updated_at",
    ]
    list_filter = ["enabled", "created_at"]
    search_fields = ["name", "description"]
    readonly_fields = ["id", "created_at", "updated_at", "created_by"]

    fieldsets = (
        (
            "Flag Configuration",
            {"fields": ("name", "enabled", "rollout_percentage", "description")},
        ),
        (
            "Metadata",
            {
                "fields": ("id", "created_by", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    def status_badge(self, obj):
        """Visual status indicator"""
        if not obj.enabled:
            color = "#dc3545"  # red
            text = "OFF"
        elif obj.rollout_percentage < 100:
            color = "#fd7e14"  # orange
            text = "PARTIAL"
        else:
            color = "#28a745"  # green
            text = "ON"

        return format_html(
            '<span style="background: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            text,
        )

    status_badge.short_description = "Status"

    def rollout_display(self, obj):
        """Show rollout percentage"""
        if not obj.enabled:
            return "-"
        return f"{obj.rollout_percentage}%"

    rollout_display.short_description = "Rollout"

    def description_preview(self, obj):
        """Truncated description"""
        if len(obj.description) > 60:
            return obj.description[:60] + "..."
        return obj.description or "-"

    description_preview.short_description = "Description"

    def save_model(self, request, obj, form, change):
        """Set created_by on first save and clear cache"""
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

        # Clear cache when flag is saved
        from apps.infrastructure.feature_flags import feature_flags

        feature_flags.clear_cache(obj.name)

    def delete_model(self, request, obj):
        """Clear cache when flag is deleted"""
        from apps.infrastructure.feature_flags import feature_flags

        flag_name = obj.name
        super().delete_model(request, obj)
        feature_flags.clear_cache(flag_name)
