# apps/core/budget_monitor.py
"""
Budget Monitoring and Alerting System
"""

import logging
from datetime import datetime
from decimal import Decimal

from django.conf import settings
from django.core.mail import send_mail
from django.db.models import Sum
from django.utils import timezone

from apps.chat.models import AnswerLog

logger = logging.getLogger(__name__)


class BudgetMonitor:
    """Monitor daily cost budget and send alerts"""

    def __init__(self):
        self.daily_budget = getattr(settings, "DAILY_COST_BUDGET_USD", 50.0)
        self.alert_threshold = getattr(settings, "BUDGET_ALERT_THRESHOLD", 0.8)
        self.alert_email = getattr(settings, "BUDGET_ALERT_EMAIL", None)

    def check_budget(self) -> dict:
        """
        Check current day's spending against budget

        Returns:
            dict with status and details
        """
        today = timezone.now().date()
        today_start = timezone.make_aware(datetime.combine(today, datetime.min.time()))

        # Get today's costs
        today_logs = AnswerLog.objects.filter(created_at__gte=today_start)

        total_cost = today_logs.aggregate(Sum("estimated_cost_usd"))[
            "estimated_cost_usd__sum"
        ] or Decimal(0)

        request_count = today_logs.count()

        # Calculate percentages
        budget_used_pct = float(total_cost) / self.daily_budget

        status = {
            "date": today.isoformat(),
            "total_cost": float(total_cost),
            "daily_budget": self.daily_budget,
            "budget_used_pct": budget_used_pct * 100,
            "request_count": request_count,
            "alert_level": self._get_alert_level(budget_used_pct),
        }

        # Send alert if needed
        if budget_used_pct >= self.alert_threshold:
            self._send_alert(status)

        return status

    def _get_alert_level(self, budget_used_pct: float) -> str:
        """Determine alert level"""
        if budget_used_pct >= 1.0:
            return "critical"
        elif budget_used_pct >= self.alert_threshold:
            return "warning"
        return "normal"

    def _send_alert(self, status: dict):
        """Send budget alert email"""
        if not self.alert_email:
            logger.warning("Budget alert triggered but no email configured")
            return

        level = status["alert_level"]
        subject = f"🚨 Budget Alert: {level.upper()}"

        message = f"""
Budget Alert for {status['date']}

Current Status:
- Total Cost: ${status['total_cost']:.2f}
- Daily Budget: ${status['daily_budget']:.2f}
- Budget Used: {status['budget_used_pct']:.1f}%
- Requests: {status['request_count']}

Alert Level: {level.upper()}

{'⚠️ BUDGET EXCEEDED!' if level == 'critical' else 'Budget threshold reached'}

View detailed report:
python manage.py cost_report --days 1 --by-model
        """

        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [self.alert_email],
                fail_silently=False,
            )
            logger.info(f"Budget alert sent to {self.alert_email}")
        except Exception as e:
            logger.error(f"Failed to send budget alert: {e}")


# Singleton instance
budget_monitor = BudgetMonitor()
