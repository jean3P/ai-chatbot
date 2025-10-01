# apps/core/tests/test_cost_tracking.py
"""Tests for cost tracking functionality"""
import pytest
from decimal import Decimal

from apps.infrastructure.pricing import calculate_cost, get_model_info


class TestPricing:
    """Test pricing calculations"""

    def test_calculate_cost_gpt4o_mini(self):
        """Test cost calculation for gpt-4o-mini"""
        cost = calculate_cost(
            prompt_tokens=1000,
            completion_tokens=500,
            model="gpt-4o-mini"
        )

        # (1000/1M * 0.150) + (500/1M * 0.600) = 0.00045
        expected = 0.00045
        assert abs(cost - expected) < 0.000001

    def test_calculate_cost_unknown_model(self):
        """Test unknown model returns 0"""
        cost = calculate_cost(1000, 500, "unknown-model")
        assert cost == 0.0

    def test_get_model_info_known(self):
        """Test getting model info for known model"""
        info = get_model_info("gpt-4o-mini")

        assert info["known"] is True
        assert info["input_price"] == 0.150
        assert info["output_price"] == 0.600

    def test_get_model_info_unknown(self):
        """Test getting model info for unknown model"""
        info = get_model_info("unknown")

        assert info["known"] is False
        assert info["input_price"] == 0.0


@pytest.mark.django_db
class TestBudgetMonitor:
    """Test budget monitoring"""

    def test_budget_check_under_limit(self):
        """Test budget check when under limit"""
        from apps.core.budget_monitor import BudgetMonitor

        monitor = BudgetMonitor()
        status = monitor.check_budget()

        assert status["alert_level"] in ["normal", "warning", "critical"]
        assert "total_cost" in status
        assert "budget_used_pct" in status

    def test_budget_alert_levels(self):
        """Test alert level calculation"""
        from apps.core.budget_monitor import BudgetMonitor

        monitor = BudgetMonitor()

        assert monitor._get_alert_level(0.5) == "normal"
        assert monitor._get_alert_level(0.85) == "warning"
        assert monitor._get_alert_level(1.1) == "critical"
