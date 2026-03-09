"""
Management command to set up default scraper schedules
"""
from django.core.management.base import BaseCommand
from django_celery_beat.models import PeriodicTask, CrontabSchedule
from scraper_manager.models import ScraperConfig
import json


class Command(BaseCommand):
    help = 'Set up default periodic task schedules for scrapers'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing scraper schedules before creating new ones',
        )
        parser.add_argument(
            '--disable',
            action='store_true',
            help='Disable all scraper schedules',
        )

    def handle(self, *args, **options):
        if options['disable']:
            self.disable_all_schedules()
            return

        if options['clear']:
            self.clear_schedules()

        self.setup_default_schedules()

    def clear_schedules(self):
        """Clear existing scraper schedules"""
        deleted = PeriodicTask.objects.filter(
            name__startswith='scraper_'
        ).delete()
        self.stdout.write(self.style.WARNING(f'Cleared {deleted[0]} existing scraper schedules'))

    def disable_all_schedules(self):
        """Disable all scraper schedules"""
        updated = PeriodicTask.objects.filter(
            name__startswith='scraper_'
        ).update(enabled=False)
        self.stdout.write(self.style.WARNING(f'Disabled {updated} scraper schedules'))

    def setup_default_schedules(self):
        """Set up default schedules for all scrapers"""
        self.stdout.write(self.style.SUCCESS('\n🕐 Setting up scraper schedules to run EVERY 3 HOURS...\n'))

        # Create every 3 hours schedule (0, 3, 6, 9, 12, 15, 18, 21 UTC)
        every_3_hours_schedule, _ = CrontabSchedule.objects.get_or_create(
            minute='0',
            hour='*/3',  # Every 3 hours
            day_of_week='*',
            day_of_month='*',
            month_of_year='*',
            timezone='UTC'
        )

        count_created = 0
        count_updated = 0

        # Set up individual scraper tasks
        for config in ScraperConfig.objects.all():
            # Every 3 hours task
            task_name = f"scraper_{config.scraper_name}_every_3_hours"
            task, created = PeriodicTask.objects.update_or_create(
                name=task_name,
                defaults={
                    'task': 'scraper_manager.run_single_scraper',
                    'crontab': every_3_hours_schedule,
                    'enabled': config.is_enabled,
                    'kwargs': json.dumps({
                        'scraper_name': config.scraper_name,
                        'max_jobs': config.max_jobs,
                        'max_pages': config.max_pages,
                    }),
                    'description': f'Scrape {config.scraper_name} every 3 hours'
                }
            )

            if created:
                count_created += 1
                self.stdout.write(f'  ✓ Created: {task_name}')
            else:
                count_updated += 1
                self.stdout.write(f'  ↻ Updated: {task_name}')

            # Update config
            config.schedule_enabled = True
            config.schedule_cron = '0 */3 * * *'  # Every 3 hours
            config.save(update_fields=['schedule_enabled', 'schedule_cron'])

        # Set up "run all scrapers" task every 3 hours
        all_task, created = PeriodicTask.objects.update_or_create(
            name='scraper_run_all_every_3_hours',
            defaults={
                'task': 'scraper_manager.run_all_scrapers',
                'crontab': every_3_hours_schedule,
                'enabled': True,
                'kwargs': json.dumps({}),
                'description': 'Run all enabled scrapers every 3 hours'
            }
        )

        if created:
            count_created += 1
            self.stdout.write(f'  ✓ Created: scraper_run_all_every_3_hours')
        else:
            count_updated += 1
            self.stdout.write(f'  ↻ Updated: scraper_run_all_every_3_hours')

        # Set up cleanup task (weekly on Sunday at 3 AM)
        cleanup_schedule, _ = CrontabSchedule.objects.get_or_create(
            minute='0',
            hour='3',
            day_of_week='0',  # Sunday
            day_of_month='*',
            month_of_year='*',
            timezone='UTC'
        )

        cleanup_task, created = PeriodicTask.objects.update_or_create(
            name='scraper_cleanup_weekly',
            defaults={
                'task': 'scraper_manager.cleanup_old_jobs',
                'crontab': cleanup_schedule,
                'enabled': True,
                'kwargs': json.dumps({'days': 30}),
                'description': 'Clean up old scraper job records every Sunday'
            }
        )

        if created:
            count_created += 1
            self.stdout.write(f'  ✓ Created: scraper_cleanup_weekly')
        else:
            count_updated += 1
            self.stdout.write(f'  ↻ Updated: scraper_cleanup_weekly')

        self.stdout.write(self.style.SUCCESS(f'\n✅ Complete: {count_created} created, {count_updated} updated\n'))
        self.stdout.write(self.style.WARNING('⚠️  Remember to start Celery Beat worker:\n'))
        self.stdout.write('   celery -A backendMain beat -l info\n')
        self.stdout.write(self.style.WARNING('And Celery worker:\n'))
        self.stdout.write('   celery -A backendMain worker -l info\n')
