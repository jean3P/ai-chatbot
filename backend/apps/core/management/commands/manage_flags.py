# apps/core/management/commands/manage_flags.py
"""
Management command for feature flags
"""
from django.core.management.base import BaseCommand, CommandError

from apps.core.models import FeatureFlag
from apps.infrastructure.feature_flags import feature_flags


class Command(BaseCommand):
    help = "Manage feature flags"

    def add_arguments(self, parser):
        parser.add_argument(
            'action',
            choices=['list', 'enable', 'disable', 'rollout', 'clear-cache'],
            help='Action to perform'
        )
        parser.add_argument(
            'flag_name',
            nargs='?',
            help='Flag name (for enable/disable/rollout)'
        )
        parser.add_argument(
            'percentage',
            nargs='?',
            type=float,
            help='Rollout percentage (0-100, for rollout action)'
        )

    def handle(self, *args, **options):
        action = options['action']

        if action == 'list':
            self.list_flags()
        elif action == 'enable':
            self.enable_flag(options['flag_name'])
        elif action == 'disable':
            self.disable_flag(options['flag_name'])
        elif action == 'rollout':
            self.set_rollout(options['flag_name'], options['percentage'])
        elif action == 'clear-cache':
            self.clear_cache()

    def list_flags(self):
        """List all feature flags"""
        flags = FeatureFlag.objects.all()

        if not flags:
            self.stdout.write(self.style.WARNING('No flags found'))
            return

        self.stdout.write('=' * 70)
        self.stdout.write(self.style.SUCCESS('Feature Flags'))
        self.stdout.write('=' * 70)

        for flag in flags:
            status = 'ON' if flag.enabled else 'OFF'
            color = self.style.SUCCESS if flag.enabled else self.style.ERROR

            self.stdout.write(f"\n{color(flag.name)} ({status})")
            self.stdout.write(f"  Rollout: {flag.rollout_percentage}%")
            self.stdout.write(f"  Description: {flag.description}")
            self.stdout.write(f"  Updated: {flag.updated_at}")

    def enable_flag(self, flag_name):
        """Enable a flag"""
        if not flag_name:
            raise CommandError('Flag name required')

        flag, created = FeatureFlag.objects.get_or_create(
            name=flag_name,
            defaults={'enabled': True, 'rollout_percentage': 100.0}
        )

        if not created:
            flag.enabled = True
            flag.save()

        feature_flags.clear_cache(flag_name)
        self.stdout.write(self.style.SUCCESS(f'Enabled {flag_name}'))

    def disable_flag(self, flag_name):
        """Disable a flag"""
        if not flag_name:
            raise CommandError('Flag name required')

        try:
            flag = FeatureFlag.objects.get(name=flag_name)
            flag.enabled = False
            flag.save()

            feature_flags.clear_cache(flag_name)
            self.stdout.write(self.style.SUCCESS(f'Disabled {flag_name}'))
        except FeatureFlag.DoesNotExist:
            raise CommandError(f'Flag {flag_name} does not exist')

    def set_rollout(self, flag_name, percentage):
        """Set rollout percentage"""
        if not flag_name:
            raise CommandError('Flag name required')
        if percentage is None:
            raise CommandError('Percentage required')

        if percentage < 0 or percentage > 100:
            raise CommandError('Percentage must be between 0 and 100')

        try:
            flag = FeatureFlag.objects.get(name=flag_name)
            flag.rollout_percentage = percentage
            flag.save()

            feature_flags.clear_cache(flag_name)
            self.stdout.write(
                self.style.SUCCESS(f'Set {flag_name} rollout to {percentage}%')
            )
        except FeatureFlag.DoesNotExist:
            raise CommandError(f'Flag {flag_name} does not exist')

    def clear_cache(self):
        """Clear flag cache"""
        feature_flags.clear_cache()
        self.stdout.write(self.style.SUCCESS('Cleared flag cache'))
