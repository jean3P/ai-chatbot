# backend/apps/core/management/commands/seed_database.py
"""
Django management command to seed database with test data
"""
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings


class Command(BaseCommand):
    help = "Seed database with test data for development and staging environments"

    def add_arguments(self, parser):
        parser.add_argument(
            "--environment",
            type=str,
            choices=["development", "staging"],
            default="development",
            help="Target environment (development or staging only)",
        )
        parser.add_argument(
            "--size",
            type=str,
            choices=["small", "medium", "large"],
            default="small",
            help="Amount of data to seed (small=10, medium=50, large=200 documents)",
        )

    def handle(self, *args, **options):
        environment = options["environment"]
        size = options["size"]

        # Prevent seeding production
        if settings.ENVIRONMENT == "production":
            raise CommandError(
                "Cannot seed database in production environment. "
                "Current ENVIRONMENT=production"
            )

        # Size mapping
        size_mapping = {"small": 10, "medium": 50, "large": 200}
        document_count = size_mapping[size]

        self.stdout.write(
            f"Would seed {document_count} documents for {environment} environment"
        )
        self.stdout.write(self.style.WARNING("Command implementation pending"))
