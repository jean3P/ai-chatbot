# apps/core/management/commands/clear_rate_limits.py
"""
Clear rate limiting cache

Useful for development and emergencies.
"""
from django.core.cache import cache
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Clear rate limiting cache"

    def add_arguments(self, parser):
        parser.add_argument(
            "--identifier",
            type=str,
            help="Clear specific identifier (e.g., 'ip:192.168.1.1' or 'user:123')",
        )

    def handle(self, *args, **options):
        identifier = options.get("identifier")

        if identifier:
            # Clear specific identifier
            self._clear_identifier(identifier)
        else:
            # Clear all rate limits
            self._clear_all()

    def _clear_identifier(self, identifier):
        """Clear rate limits for specific identifier"""
        periods = ["min", "hour", "day"]
        cleared = 0

        for period in periods:
            cache_key = f"rate_limit:{identifier}:{period}"
            if cache.delete(cache_key):
                cleared += 1

        self.stdout.write(
            self.style.SUCCESS(f"Cleared {cleared} rate limits for {identifier}")
        )

    def _clear_all(self):
        """Clear all rate limiting cache entries"""
        self.stdout.write("Clearing all rate limit entries...")

        # Django's cache doesn't have a native "clear all by pattern" method
        # So we clear the entire cache (safe for development)
        cache.clear()

        self.stdout.write(
            self.style.SUCCESS("Cleared all cache entries (including rate limits)")
        )
        self.stdout.write(
            self.style.WARNING(
                "Note: This clears ALL cache, not just rate limits. "
                "Use --identifier to clear specific entries."
            )
        )
