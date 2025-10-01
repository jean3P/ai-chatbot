# apps/core/throttling.py
"""
Django REST Framework Throttle Classes

Custom throttling for different user types and endpoints.
"""
import logging

from django.conf import settings
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle

from apps.infrastructure.rate_limit import get_rate_limit_config

logger = logging.getLogger(__name__)


class ConfigurableAnonRateThrottle(AnonRateThrottle):
    """
    Anonymous user throttling with environment-based rates

    Rate limit based on IP address.
    """

    def __init__(self):
        super().__init__()
        config = get_rate_limit_config(settings.ENVIRONMENT)
        self.rate = config.get("anon_rate", "100/min")

    def allow_request(self, request, view):
        """Check if request is allowed"""
        config = get_rate_limit_config(settings.ENVIRONMENT)

        if not config.get("enabled", True):
            return True  # Rate limiting disabled

        allowed = super().allow_request(request, view)

        if not allowed:
            logger.warning(
                f"Rate limit exceeded for IP {self.get_ident(request)} "
                f"on {request.path}"
            )

        return allowed


class ConfigurableUserRateThrottle(UserRateThrottle):
    """
    Authenticated user throttling with environment-based rates

    Rate limit based on user ID.
    """

    def __init__(self):
        super().__init__()
        config = get_rate_limit_config(settings.ENVIRONMENT)
        self.rate = config.get("user_rate", "1000/hour")

    def allow_request(self, request, view):
        """Check if request is allowed"""
        config = get_rate_limit_config(settings.ENVIRONMENT)

        if not config.get("enabled", True):
            return True

        allowed = super().allow_request(request, view)

        if not allowed:
            user_id = request.user.id if request.user.is_authenticated else "anon"
            logger.warning(f"Rate limit exceeded for user {user_id} on {request.path}")

        return allowed


class ChatEndpointThrottle(AnonRateThrottle):
    """
    Strict rate limiting for expensive chat endpoints

    Prevents runaway LLM costs from abuse.
    """

    scope = "chat"

    def __init__(self):
        super().__init__()
        config = get_rate_limit_config(settings.ENVIRONMENT)
        self.rate = config.get("chat_rate", "50/min")


class UploadEndpointThrottle(AnonRateThrottle):
    """
    Rate limiting for document upload endpoints

    Prevents storage abuse.
    """

    scope = "upload"

    def __init__(self):
        super().__init__()
        config = get_rate_limit_config(settings.ENVIRONMENT)
        self.rate = config.get("upload_rate", "10/hour")


class BurstProtectionThrottle(AnonRateThrottle):
    """
    Short-term burst protection

    Prevents rapid-fire requests regardless of hourly limit.
    """

    def __init__(self):
        super().__init__()
        config = get_rate_limit_config(settings.ENVIRONMENT)
        self.rate = config.get("burst_rate", "20/min")
