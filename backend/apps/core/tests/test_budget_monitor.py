# apps/core/tests/test_budget_monitor.py
"""
Tests for budget monitoring and alerting
"""
import pytest
from datetime import timedelta
from decimal import Decimal
from django.utils import timezone

from apps.core.budget_monitor import BudgetMonitor
from apps.chat.models import AnswerLog, Message, Conversation


@pytest.mark.django_db
class TestBudgetMonitor:
    """Test budget monitoring functionality"""

    def setup_method(self):
        """Create test data before each test"""
        self.monitor = BudgetMonitor()
        # Override budget for testing
        self.monitor.daily_budget = 1.0  # $1 daily budget

        # Create test conversation and message
        self.conversation = Conversation.objects.create(
            session_id="test-session",
            language="en",
            title="Test"
        )

        self.message = Message.objects.create(
            conversation=self.conversation,
            role="assistant",
            content="Test response"
        )

    def test_budget_check_empty_database(self):
        """Test budget check with no spending"""
        status = self.monitor.check_budget()

        assert status["total_cost"] == 0.0
        assert status["budget_used_pct"] == 0.0
        assert status["alert_level"] == "normal"
        assert status["request_count"] == 0

    def test_budget_check_under_threshold(self):
        """Test budget check when spending is under alert threshold"""
        # Add log with 50% of budget spent
        AnswerLog.objects.create(
            message=self.message,
            query="test query",
            language="en",
            method="baseline",
            llm_model="gpt-4o-mini",
            embedding_model="test",
            total_tokens=1000,
            prompt_tokens=800,
            completion_tokens=200,
            total_latency_ms=500,
            estimated_cost_usd=Decimal("0.50"),  # 50% of $1 budget
        )

        status = self.monitor.check_budget()

        assert status["total_cost"] == 0.50
        assert status["budget_used_pct"] == 50.0
        assert status["alert_level"] == "normal"

    def test_budget_check_warning_threshold(self):
        """Test budget check at warning threshold (80%)"""
        AnswerLog.objects.create(
            message=self.message,
            query="test query",
            language="en",
            method="baseline",
            llm_model="gpt-4o-mini",
            embedding_model="test",
            total_tokens=1000,
            prompt_tokens=800,
            completion_tokens=200,
            total_latency_ms=500,
            estimated_cost_usd=Decimal("0.85"),  # 85% of budget
        )

        status = self.monitor.check_budget()

        assert status["alert_level"] == "warning"
        assert status["budget_used_pct"] == 85.0

    def test_budget_check_critical_threshold(self):
        """Test budget check when budget exceeded"""
        AnswerLog.objects.create(
            message=self.message,
            query="test query",
            language="en",
            method="baseline",
            llm_model="gpt-4o-mini",
            embedding_model="test",
            total_tokens=1000,
            prompt_tokens=800,
            completion_tokens=200,
            total_latency_ms=500,
            estimated_cost_usd=Decimal("1.50"),  # 150% of budget
        )

        status = self.monitor.check_budget()

        assert status["alert_level"] == "critical"
        assert status["budget_used_pct"] == 150.0
        assert status["total_cost"] == 1.50

    def test_multiple_requests_accumulate(self):
        """Test that multiple requests add up"""
        # Add 3 requests at $0.30 each = $0.90 total
        for i in range(3):
            message = Message.objects.create(
                conversation=self.conversation,
                role="assistant",
                content=f"Response {i}"
            )
            AnswerLog.objects.create(
                message=message,
                query=f"query {i}",
                language="en",
                method="baseline",
                llm_model="gpt-4o-mini",
                embedding_model="test",
                total_tokens=1000,
                prompt_tokens=800,
                completion_tokens=200,
                total_latency_ms=500,
                estimated_cost_usd=Decimal("0.30"),
            )

        status = self.monitor.check_budget()

        assert status["total_cost"] == 0.90
        assert status["request_count"] == 3
        assert status["alert_level"] == "warning"  # 90% > 80%

    def test_only_counts_today(self):
        """Test that only today's requests count toward budget"""
        # Add yesterday's log (should not count)
        yesterday_message = Message.objects.create(
            conversation=self.conversation,
            role="assistant",
            content="Yesterday response"
        )
        yesterday_log = AnswerLog.objects.create(
            message=yesterday_message,
            query="yesterday query",
            language="en",
            method="baseline",
            llm_model="gpt-4o-mini",
            embedding_model="test",
            total_tokens=1000,
            prompt_tokens=800,
            completion_tokens=200,
            total_latency_ms=500,
            estimated_cost_usd=Decimal("5.00"),  # Large amount
        )
        # Manually set to yesterday
        yesterday_log.created_at = timezone.now() - timedelta(days=1)
        yesterday_log.save()

        # Add today's log
        AnswerLog.objects.create(
            message=self.message,
            query="today query",
            language="en",
            method="baseline",
            llm_model="gpt-4o-mini",
            embedding_model="test",
            total_tokens=1000,
            prompt_tokens=800,
            completion_tokens=200,
            total_latency_ms=500,
            estimated_cost_usd=Decimal("0.10"),
        )

        status = self.monitor.check_budget()

        # Should only count today's $0.10
        assert status["total_cost"] == 0.10
        assert status["request_count"] == 1

    def test_alert_level_calculation(self):
        """Test alert level determination"""
        assert self.monitor._get_alert_level(0.0) == "normal"
        assert self.monitor._get_alert_level(0.5) == "normal"
        assert self.monitor._get_alert_level(0.79) == "normal"
        assert self.monitor._get_alert_level(0.80) == "warning"
        assert self.monitor._get_alert_level(0.99) == "warning"
        assert self.monitor._get_alert_level(1.0) == "critical"
        assert self.monitor._get_alert_level(1.5) == "critical"
