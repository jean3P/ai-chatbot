# apps/infrastructure/feature_flags.py
"""
Feature Flag Service

Provides centralized feature flag checking with caching and percentage rollouts.
"""
import hashlib
import logging
from typing import Optional

from django.core.cache import cache
from django.conf import settings

logger = logging.getLogger(__name__)

# Cache TTL for flags (5 minutes)
FLAG_CACHE_TTL = 300


class FeatureFlagService:
    """
    Service for checking feature flags

    Supports:
    - Global enable/disable
    - Percentage-based rollouts
    - Caching for performance
    - Fallback to environment variables
    """

    def __init__(self):
        self.cache_prefix = "feature_flag:"

    def is_enabled(
            self,
            flag_name: str,
            user_id: Optional[str] = None,
            session_id: Optional[str] = None,
            default: bool = False
    ) -> bool:
        """
        Check if a feature flag is enabled

        Args:
            flag_name: Name of the flag
            user_id: Optional user ID for percentage rollout
            session_id: Optional session ID for percentage rollout
            default: Default value if flag doesn't exist

        Returns:
            True if flag is enabled for this user/session
        """
        # Check cache first
        cache_key = self._get_cache_key(flag_name)
        cached_flag = cache.get(cache_key)

        if cached_flag is not None:
            flag_data = cached_flag
        else:
            # Load from database
            flag_data = self._load_flag_from_db(flag_name)

            if flag_data is None:
                # Fallback to environment variable
                env_value = getattr(settings, flag_name, None)
                if env_value is not None:
                    logger.info(f"Flag {flag_name} not in DB, using env: {env_value}")
                    return bool(env_value)

                logger.debug(f"Flag {flag_name} not found, using default: {default}")
                return default

            # Cache the flag data
            cache.set(cache_key, flag_data, FLAG_CACHE_TTL)

        # Check if flag is globally disabled
        if not flag_data['enabled']:
            return False

        # Check rollout percentage
        rollout_pct = flag_data['rollout_percentage']

        # Full rollout
        if rollout_pct >= 100:
            return True

        # No rollout
        if rollout_pct <= 0:
            return False

        # Partial rollout - check if user/session is in rollout
        identifier = user_id or session_id or "anonymous"
        return self._is_in_rollout(flag_name, identifier, rollout_pct)

    def _load_flag_from_db(self, flag_name: str) -> Optional[dict]:
        """Load flag from database"""
        try:
            from apps.core.models import FeatureFlag

            flag = FeatureFlag.objects.filter(name=flag_name).first()
            if not flag:
                return None

            return {
                'enabled': flag.enabled,
                'rollout_percentage': float(flag.rollout_percentage),
                'description': flag.description,
            }
        except Exception as e:
            logger.error(f"Error loading flag {flag_name}: {e}")
            return None

    def _is_in_rollout(self, flag_name: str, identifier: str, rollout_pct: float) -> bool:
        """
        Determine if identifier is in rollout percentage

        Uses consistent hashing to ensure same user always gets same result.
        """
        # Create hash of flag_name + identifier
        hash_input = f"{flag_name}:{identifier}".encode('utf-8')
        hash_value = int(hashlib.md5(hash_input).hexdigest(), 16)

        # Convert to percentage (0-100)
        user_percentage = (hash_value % 100) + 1

        # Check if user falls within rollout
        return user_percentage <= rollout_pct

    def _get_cache_key(self, flag_name: str) -> str:
        """Generate cache key for flag"""
        return f"{self.cache_prefix}{flag_name}"

    def clear_cache(self, flag_name: Optional[str] = None):
        """
        Clear flag cache

        Args:
            flag_name: Specific flag to clear, or None for all flags
        """
        if flag_name:
            cache_key = self._get_cache_key(flag_name)
            cache.delete(cache_key)
            logger.info(f"Cleared cache for flag: {flag_name}")
        else:
            # Clear all flag caches - iterate through known keys
            try:
                from apps.core.models import FeatureFlag
                for flag in FeatureFlag.objects.all():
                    cache_key = self._get_cache_key(flag.name)
                    cache.delete(cache_key)
            except:
                pass
            logger.info("Cleared all flag caches")

    def get_all_flags(self) -> dict:
        """
        Get all flags and their status

        Returns:
            Dictionary of flag_name -> status
        """
        try:
            from apps.core.models import FeatureFlag

            flags = {}
            for flag in FeatureFlag.objects.all():
                flags[flag.name] = {
                    'enabled': flag.enabled,
                    'rollout_percentage': float(flag.rollout_percentage),
                    'description': flag.description,
                }
            return flags
        except Exception as e:
            logger.error(f"Error getting all flags: {e}")
            return {}


# Global instance
feature_flags = FeatureFlagService()
