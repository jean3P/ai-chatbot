# apps/core/management/commands/cost_report.py

"""
Cost Report Management Command

Usage:
    python manage.py cost_report
    python manage.py cost_report --days 7
    python manage.py cost_report --by-model
"""
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand
from django.db.models import Count, Sum
from django.utils import timezone

from apps.chat.models import AnswerLog


class Command(BaseCommand):
    help = "Generate cost report for LLM usage"

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=1,
            help="Number of days to report (default: 1 for today)",
        )
        parser.add_argument(
            "--by-model",
            action="store_true",
            help="Break down costs by model",
        )
        parser.add_argument(
            "--by-method",
            action="store_true",
            help="Break down costs by RAG method",
        )
        parser.add_argument(
            "--export-csv",
            type=str,
            help="Export to CSV file",
        )

    def handle(self, *args, **options):
        days = options["days"]
        by_model = options["by_model"]
        by_method = options["by_method"]
        export_csv = options["export_csv"]

        # Calculate date range
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)

        self.stdout.write("=" * 70)
        self.stdout.write(
            self.style.SUCCESS(
                f"Cost Report: {start_date.date()} to {end_date.date()}"
            )
        )
        self.stdout.write("=" * 70)

        # Overall statistics
        logs = AnswerLog.objects.filter(created_at__gte=start_date)

        total_requests = logs.count()
        total_cost = logs.aggregate(Sum("estimated_cost_usd"))[
                         "estimated_cost_usd__sum"
                     ] or 0.0
        total_tokens = logs.aggregate(Sum("total_tokens"))["total_tokens__sum"] or 0

        # Calculate average latency safely
        avg_latency = 0
        if total_requests > 0:
            total_latency_sum = logs.aggregate(Sum("total_latency_ms"))[
                                    "total_latency_ms__sum"
                                ] or 0
            avg_latency = total_latency_sum / total_requests

        self.stdout.write(f"\nTotal Requests: {total_requests}")
        self.stdout.write(self.style.WARNING(f"Total Cost: ${total_cost:.2f}"))
        self.stdout.write(f"Total Tokens: {total_tokens:,}")
        self.stdout.write(f"Average Latency: {avg_latency:.0f}ms")

        # Safe cost per request calculation
        if total_requests > 0:
            self.stdout.write(f"Cost per Request: ${total_cost / total_requests:.4f}")
        else:
            self.stdout.write("Cost per Request: N/A (no requests)")

        # By model breakdown
        if by_model:
            self.stdout.write("\n" + "-" * 70)
            self.stdout.write(self.style.SUCCESS("Breakdown by Model:"))
            self.stdout.write("-" * 70)

            model_stats = (
                logs.values("llm_model")
                .annotate(
                    count=Count("id"),
                    total_cost=Sum("estimated_cost_usd"),
                    total_tokens=Sum("total_tokens"),
                )
                .order_by("-total_cost")
            )

            for stat in model_stats:
                model = stat["llm_model"]
                count = stat["count"]
                cost = stat["total_cost"] or 0.0
                tokens = stat["total_tokens"] or 0

                self.stdout.write(
                    f"\n{model}:"
                )
                self.stdout.write(f"  Requests: {count}")
                self.stdout.write(f"  Cost: ${cost:.2f}")
                self.stdout.write(f"  Tokens: {tokens:,}")
                self.stdout.write(f"  Avg Cost/Request: ${cost / count:.4f}")

        # By method breakdown
        if by_method:
            self.stdout.write("\n" + "-" * 70)
            self.stdout.write(self.style.SUCCESS("Breakdown by RAG Method:"))
            self.stdout.write("-" * 70)

            method_stats = (
                logs.values("method")
                .annotate(
                    count=Count("id"),
                    total_cost=Sum("estimated_cost_usd"),
                    avg_chunks=Sum("chunks_used") / Count("id"),
                )
                .order_by("-total_cost")
            )

            for stat in method_stats:
                method = stat["method"]
                count = stat["count"]
                cost = stat["total_cost"] or 0.0
                avg_chunks = stat["avg_chunks"] or 0.0

                self.stdout.write(f"\n{method}:")
                self.stdout.write(f"  Requests: {count}")
                self.stdout.write(f"  Cost: ${cost:.2f}")
                self.stdout.write(f"  Avg Chunks: {avg_chunks:.1f}")

        # Daily breakdown
        if days > 1:
            self.stdout.write("\n" + "-" * 70)
            self.stdout.write(self.style.SUCCESS("Daily Breakdown:"))
            self.stdout.write("-" * 70)

            for day_offset in range(days):
                day = start_date + timedelta(days=day_offset)
                next_day = day + timedelta(days=1)

                day_logs = logs.filter(
                    created_at__gte=day,
                    created_at__lt=next_day
                )

                day_cost = day_logs.aggregate(Sum("estimated_cost_usd"))[
                               "estimated_cost_usd__sum"
                           ] or 0.0
                day_count = day_logs.count()

                self.stdout.write(
                    f"{day.date()}: {day_count} requests, ${day_cost:.2f}"
                )

        # Budget check
        from django.conf import settings
        daily_budget = getattr(settings, 'DAILY_COST_BUDGET_USD', None)

        if daily_budget:
            today_logs = logs.filter(created_at__gte=timezone.now().date())
            today_cost = today_logs.aggregate(Sum("estimated_cost_usd"))[
                             "estimated_cost_usd__sum"
                         ] or 0.0

            budget_pct = (today_cost / daily_budget) * 100

            self.stdout.write("\n" + "=" * 70)
            self.stdout.write(f"Today's Budget: ${today_cost:.2f} / ${daily_budget:.2f}")

            if budget_pct > 100:
                self.stdout.write(
                    self.style.ERROR(f"⚠️  BUDGET EXCEEDED: {budget_pct:.1f}%")
                )
            elif budget_pct > 80:
                self.stdout.write(
                    self.style.WARNING(f"⚠️  Budget usage: {budget_pct:.1f}%")
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Budget usage: {budget_pct:.1f}%")
                )

        # Export CSV
        if export_csv:
            self._export_csv(logs, export_csv)
            self.stdout.write(
                self.style.SUCCESS(f"\n✓ Exported to {export_csv}")
            )

    def _export_csv(self, logs, filename):
        """Export logs to CSV"""
        import csv

        with open(filename, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([
                'Timestamp', 'Method', 'Model', 'Tokens',
                'Cost (USD)', 'Latency (ms)', 'Language'
            ])

            for log in logs:
                writer.writerow([
                    log.created_at.isoformat(),
                    log.method,
                    log.llm_model,
                    log.total_tokens,
                    f"{log.estimated_cost_usd:.4f}",
                    f"{log.total_latency_ms:.0f}",
                    log.language,
                ])
