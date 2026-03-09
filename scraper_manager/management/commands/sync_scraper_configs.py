"""
Management command to sync scraper configurations.
Auto-creates ScraperConfig entries for all registered scrapers.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from scraper_manager.scrapers import SCRAPERS
from scraper_manager.models import ScraperConfig


class Command(BaseCommand):
    help = 'Sync scraper configurations - creates configs for all registered scrapers'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without actually creating',
        )
        parser.add_argument(
            '--enable-all',
            action='store_true',
            help='Enable all scrapers by default',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        enable_all = options['enable_all']
        
        self.stdout.write(self.style.SUCCESS('='*70))
        self.stdout.write(self.style.SUCCESS('SCRAPER CONFIGURATION SYNC'))
        self.stdout.write(self.style.SUCCESS('='*70))
        
        total_scrapers = len(SCRAPERS)
        created_count = 0
        updated_count = 0
        skipped_count = 0
        
        self.stdout.write(f'\nFound {total_scrapers} registered scrapers\n')
        
        for scraper_name in sorted(SCRAPERS.keys()):
            try:
                config, created = ScraperConfig.objects.get_or_create(
                    scraper_name=scraper_name,
                    defaults={
                        'is_enabled': enable_all,
                        'max_jobs': 50,
                        'max_pages': 5,
                        'timeout': 300,
                        'retry_count': 3,
                        'schedule_enabled': False,
                    }
                )
                
                if dry_run:
                    if created:
                        self.stdout.write(
                            self.style.WARNING(f'  [DRY RUN] Would create: {scraper_name}')
                        )
                        created_count += 1
                    else:
                        self.stdout.write(
                            self.style.NOTICE(f'  [DRY RUN] Already exists: {scraper_name}')
                        )
                        skipped_count += 1
                else:
                    if created:
                        self.stdout.write(
                            self.style.SUCCESS(f'  ✓ Created config for: {scraper_name}')
                        )
                        created_count += 1
                    else:
                        self.stdout.write(
                            self.style.NOTICE(f'  - Already configured: {scraper_name}')
                        )
                        skipped_count += 1
                        
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'  ✗ Error with {scraper_name}: {str(e)}')
                )
        
        # Summary
        self.stdout.write('\n' + '='*70)
        self.stdout.write(self.style.SUCCESS('SUMMARY'))
        self.stdout.write('='*70)
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\n[DRY RUN MODE - No changes made]'))
        
        self.stdout.write(f'\nTotal scrapers: {total_scrapers}')
        self.stdout.write(self.style.SUCCESS(f'Created: {created_count}'))
        self.stdout.write(self.style.NOTICE(f'Already configured: {skipped_count}'))
        
        if created_count > 0 and not dry_run:
            self.stdout.write(
                self.style.SUCCESS(f'\n✓ Successfully created {created_count} scraper configuration(s)!')
            )
            self.stdout.write('\nNext steps:')
            self.stdout.write('  1. Go to admin panel: /admin/scraper_manager/scraperconfig/')
            self.stdout.write('  2. Enable desired scrapers')
            self.stdout.write('  3. Configure limits and schedules')
            self.stdout.write('  4. Run scrapers manually or set up schedules')
        elif dry_run:
            self.stdout.write(
                self.style.WARNING(f'\nRun without --dry-run to create {created_count} configuration(s)')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('\n✓ All scrapers already configured!')
            )
        
        self.stdout.write('')
