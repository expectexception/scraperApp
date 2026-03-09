"""
Management command to configure and manage scraper schedules
"""
from django.core.management.base import BaseCommand
from scraper_manager.config import AUTO_SCHEDULE

class Command(BaseCommand):
    help = 'Manage scraper schedules - view or update AUTO_SCHEDULE configuration'

    def add_arguments(self, parser):
        parser.add_argument(
            'action',
            type=str,
            choices=['view', 'enable', 'disable', 'update'],
            help='Action to perform'
        )
        parser.add_argument(
            '--schedule',
            type=str,
            help='Schedule name (run_all_scrapers, run_priority_scrapers, run_specialty_scrapers, cleanup_old_jobs, generate_report)'
        )
        parser.add_argument(
            '--cron',
            type=str,
            help='Cron expression (e.g., "0 */3 * * *" for every 3 hours)'
        )

    def handle(self, *args, **options):
        action = options['action']
        
        if action == 'view':
            self.view_schedules()
        elif action == 'enable':
            self.enable_schedule(options.get('schedule'))
        elif action == 'disable':
            self.disable_schedule(options.get('schedule'))
        elif action == 'update':
            self.update_schedule(options.get('schedule'), options.get('cron'))

    def view_schedules(self):
        """Display all schedules"""
        self.stdout.write(self.style.SUCCESS('\n📋 SCRAPER AUTO-SCHEDULES\n'))
        self.stdout.write(f"Global Auto-Schedule: {'✅ ENABLED' if AUTO_SCHEDULE.get('enabled') else '❌ DISABLED'}\n")
        
        schedules = [
            ('run_all_scrapers', 'Run all enabled scrapers'),
            ('run_priority_scrapers', 'Run high-priority scrapers'),
            ('run_specialty_scrapers', 'Run specialty airline scrapers'),
            ('cleanup_old_jobs', 'Archive/cleanup old jobs'),
            ('generate_report', 'Generate daily scraper report'),
        ]
        
        for key, desc in schedules:
            schedule = AUTO_SCHEDULE.get(key, {})
            enabled = schedule.get('enabled', False)
            cron = schedule.get('schedule', 'N/A')
            status = self.style.SUCCESS('✅') if enabled else self.style.ERROR('❌')
            
            self.stdout.write(f"\n{status} {key}")
            self.stdout.write(f"   Description: {desc}")
            self.stdout.write(f"   Cron: {cron}")
            self.stdout.write(f"   Enabled: {enabled}")
            
            if 'scrapers' in schedule:
                self.stdout.write(f"   Scrapers: {', '.join(schedule['scrapers'])}")
            if 'max_jobs' in schedule:
                self.stdout.write(f"   Max Jobs: {schedule.get('max_jobs', 'unlimited')}")

    def enable_schedule(self, schedule_name):
        """Enable a specific schedule"""
        if not schedule_name:
            self.stdout.write(self.style.ERROR('Please specify --schedule'))
            return
        
        if schedule_name not in AUTO_SCHEDULE:
            self.stdout.write(self.style.ERROR(f'Schedule "{schedule_name}" not found'))
            return
        
        self.stdout.write(self.style.WARNING(f'\nTo enable: Edit scraper_manager/config.py'))
        self.stdout.write(f'Set: AUTO_SCHEDULE["{schedule_name}"]["enabled"] = True')
        self.stdout.write('Then restart Celery: celery -A backendMain worker -l info')

    def disable_schedule(self, schedule_name):
        """Disable a specific schedule"""
        if not schedule_name:
            self.stdout.write(self.style.ERROR('Please specify --schedule'))
            return
        
        self.stdout.write(self.style.WARNING(f'\nTo disable: Edit scraper_manager/config.py'))
        self.stdout.write(f'Set: AUTO_SCHEDULE["{schedule_name}"]["enabled"] = False')
        self.stdout.write('Then restart Celery: celery -A backendMain worker -l info')

    def update_schedule(self, schedule_name, cron):
        """Update cron schedule"""
        if not schedule_name or not cron:
            self.stdout.write(self.style.ERROR('Please specify --schedule and --cron'))
            return
        
        self.stdout.write(self.style.WARNING(f'\nTo update: Edit scraper_manager/config.py'))
        self.stdout.write(f'Set: AUTO_SCHEDULE["{schedule_name}"]["schedule"] = "{cron}"')
        self.stdout.write('Then restart Celery: celery -A backendMain worker -l info')
        self.stdout.write(f'\nExample cron expressions:')
        self.stdout.write('  "0 */3 * * *" = Every 3 hours')
        self.stdout.write('  "0 */6 * * *" = Every 6 hours')
        self.stdout.write('  "0 1 * * *" = Daily at 01:00')
        self.stdout.write('  "0 0 * * 0" = Weekly on Sunday at 00:00')
