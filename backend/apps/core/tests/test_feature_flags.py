# apps/core/tests/test_feature_flags.py
"""Tests for feature flag system"""
import pytest

from apps.core.models import FeatureFlag
from apps.infrastructure.feature_flags import FeatureFlagService


@pytest.mark.django_db
class TestFeatureFlagModel:
    """Test FeatureFlag model"""

    def test_create_flag(self):
        """Test creating a feature flag"""
        flag = FeatureFlag.objects.create(
            name='TEST_FLAG',
            enabled=True,
            rollout_percentage=50.0,
            description='Test flag'
        )

        assert flag.name == 'TEST_FLAG'
        assert flag.enabled is True
        assert flag.rollout_percentage == 50.0
        assert not flag.is_full_rollout

    def test_full_rollout_property(self):
        """Test is_full_rollout property"""
        flag = FeatureFlag.objects.create(
            name='FULL_FLAG',
            enabled=True,
            rollout_percentage=100.0
        )

        assert flag.is_full_rollout


@pytest.mark.django_db
class TestFeatureFlagService:
    """Test FeatureFlagService"""

    def setup_method(self):
        """Setup test service"""
        self.service = FeatureFlagService()
        self.service.clear_cache()

    def test_flag_enabled_full_rollout(self):
        """Test flag with full rollout"""
        FeatureFlag.objects.create(
            name='FULL_FLAG',
            enabled=True,
            rollout_percentage=100.0
        )

        assert self.service.is_enabled('FULL_FLAG') is True

    def test_flag_disabled(self):
        """Test disabled flag"""
        FeatureFlag.objects.create(
            name='DISABLED_FLAG',
            enabled=False,
            rollout_percentage=100.0
        )

        assert self.service.is_enabled('DISABLED_FLAG') is False

    def test_flag_not_found_uses_default(self):
        """Test non-existent flag uses default"""
        assert self.service.is_enabled('NONEXISTENT', default=True) is True
        assert self.service.is_enabled('NONEXISTENT', default=False) is False
