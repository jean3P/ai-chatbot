# apps/infrastructure/rate_limit.py
"""
Rate Limiting Configuration

Defines rate limits per environment and provides helper functions.
"""
from typing import Dict, Tuple

# Rate limit configurations by environment
RATE_LIMIT_CONFIGS = {
    "test": {
        "enabled": True,  # Disable in tests for speed
        "anon_rate": "1000/min",  # Permissive for tests
        "user_rate": "10000/hour",
    },
    "development": {
        "enabled": True,
        "anon_rate": "100/min",  # Per-IP limit
        "user_rate": "1000/hour",  # Per-authenticated-user limit
        "burst_rate": "20/min",  # Short burst protection
    },
    "staging": {
        "enabled": True,
        "anon_rate": "100/min",
        "user_rate": "1000/hour",
        "burst_rate": "20/min",
    },
    "production": {
        "enabled": True,
        "anon_rate": "100/min",
        "user_rate": "1000/hour",
        "burst_rate": "20/min",
        # Stricter for expensive endpoints
        "chat_rate": "50/min",  # LLM calls
        "upload_rate": "10/hour",  # Document uploads
    },
}


def get_rate_limit_config(environment: str) -> Dict:
    """
    Get rate limit configuration for environment

    Args:
        environment: Environment name (test, development, staging, production)

    Returns:
        Configuration dictionary
    """
    return RATE_LIMIT_CONFIGS.get(environment, RATE_LIMIT_CONFIGS["development"])


def parse_rate(rate_string: str) -> Tuple[int, str]:
    """
    Parse rate string like "100/min" into (100, "min")

    Args:
        rate_string: Rate in format "number/period"

    Returns:
        Tuple of (number, period)
    """
    try:
        number, period = rate_string.split("/")
        return int(number), period
    except (ValueError, AttributeError):
        return 100, "min"  # Default fallback


def format_retry_after(rate_string: str) -> int:
    """
    Calculate Retry-After header value in seconds

    Args:
        rate_string: Rate in format "number/period"

    Returns:
        Seconds to wait
    """
    _, period = parse_rate(rate_string)

    period_seconds = {
        "s": 1,
        "sec": 1,
        "second": 1,
        "m": 60,
        "min": 60,
        "minute": 60,
        "h": 3600,
        "hour": 3600,
        "d": 86400,
        "day": 86400,
    }

    return period_seconds.get(period, 60)  # Default to 60 seconds
