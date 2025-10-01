# apps/core/middleware.py
"""
Rate Limiting Middleware

Provides rate limiting at the middleware level with custom headers.
"""
import logging

from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin

from apps.infrastructure.rate_limit import (
    format_retry_after,
    get_rate_limit_config,
    parse_rate,
)

logger = logging.getLogger(__name__)


class RateLimitMiddleware(MiddlewareMixin):
    """
    Middleware for global rate limiting

    Tracks requests per IP and optionally per user.
    """

    # Declare middleware capabilities
    sync_capable = True
    async_capable = False

    def __init__(self, get_response):
        super().__init__(get_response)
        self.config = get_rate_limit_config(settings.ENVIRONMENT)
        self.enabled = self.config.get("enabled", True)

    def process_request(self, request):
        """Check rate limits before processing request"""
        if not self.enabled:
            return None

        # Skip rate limiting for certain paths
        if self._should_skip_rate_limit(request):
            return None

        # Get identifier (IP or user ID)
        identifier = self._get_identifier(request)

        # Check if rate limited
        if self._is_rate_limited(identifier, request):
            return self._rate_limit_response(identifier, request)

        # Increment counter after successful check
        self._increment_counter(identifier)

        return None

    def process_response(self, request, response):
        """Add rate limit headers to response"""
        if not self.enabled:
            return response

        identifier = self._get_identifier(request)
        rate_info = self._get_rate_info(identifier)

        # Add informational headers
        response["X-RateLimit-Limit"] = rate_info["limit"]
        response["X-RateLimit-Remaining"] = rate_info["remaining"]
        response["X-RateLimit-Reset"] = rate_info["reset"]

        return response

    def _should_skip_rate_limit(self, request):
        """Skip rate limiting for certain paths"""
        skip_paths = [
            "/admin/",
            "/static/",
            "/media/",
            "/api/health/",
        ]
        return any(request.path.startswith(path) for path in skip_paths)

    def _get_identifier(self, request):
        """Get unique identifier for rate limiting"""
        # Prefer authenticated user
        if request.user and request.user.is_authenticated:
            return f"user:{request.user.id}"

        # Fallback to IP address
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0].strip()
        else:
            ip = request.META.get("REMOTE_ADDR")

        return f"ip:{ip}"

    def _is_rate_limited(self, identifier, request):
        """Check if identifier has exceeded rate limit"""
        # Get appropriate rate for this identifier
        if identifier.startswith("user:"):
            rate_string = self.config.get("user_rate", "1000/hour")
        else:
            rate_string = self.config.get("anon_rate", "100/min")

        limit, period = parse_rate(rate_string)

        # Get current request count
        cache_key = f"rate_limit:{identifier}:{period}"
        current_count = cache.get(cache_key, 0)

        return current_count >= limit

    def _increment_counter(self, identifier):
        """Increment request counter"""
        # Get appropriate rate
        if identifier.startswith("user:"):
            rate_string = self.config.get("user_rate", "1000/hour")
        else:
            rate_string = self.config.get("anon_rate", "100/min")

        limit, period = parse_rate(rate_string)
        cache_key = f"rate_limit:{identifier}:{period}"

        # Calculate timeout in seconds
        timeout_map = {
            "min": 60,
            "minute": 60,
            "hour": 3600,
            "day": 86400,
        }
        timeout = timeout_map.get(period, 60)

        # Atomic increment
        try:
            current = cache.get(cache_key, 0)
            cache.set(cache_key, current + 1, timeout=timeout)
        except Exception as e:
            logger.error(f"Failed to increment rate limit counter: {e}")

    def _get_rate_info(self, identifier):
        """Get current rate limit info for headers"""
        if identifier.startswith("user:"):
            rate_string = self.config.get("user_rate", "1000/hour")
        else:
            rate_string = self.config.get("anon_rate", "100/min")

        limit, period = parse_rate(rate_string)
        cache_key = f"rate_limit:{identifier}:{period}"
        current_count = cache.get(cache_key, 0)

        return {
            "limit": limit,
            "remaining": max(0, limit - current_count),
            "reset": format_retry_after(rate_string),
        }

    def _rate_limit_response(self, identifier, request):
        """Return 429 Rate Limited response"""
        if identifier.startswith("user:"):
            rate_string = self.config.get("user_rate", "1000/hour")
        else:
            rate_string = self.config.get("anon_rate", "100/min")

        retry_after = format_retry_after(rate_string)

        logger.warning(
            f"Rate limit exceeded: {identifier} on {request.path} "
            f"({request.method})"
        )

        response = JsonResponse(
            {
                "error": "Rate limit exceeded",
                "message": f"Too many requests. Please try again in {retry_after} seconds.",
                "retry_after": retry_after,
            },
            status=429,
        )

        response["Retry-After"] = str(retry_after)
        response["X-RateLimit-Limit"] = parse_rate(rate_string)[0]
        response["X-RateLimit-Remaining"] = 0
        response["X-RateLimit-Reset"] = retry_after

        return response
