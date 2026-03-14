"""
Django management command to run scrapers
Usage: python manage.py run_scraper [scraper_name] [options]
"""

import asyncio
import sys
import os
import logging
from concurrent.futures import ThreadPoolExecutor
from django.core.management.base import BaseCommand
from django.utils import timezone
from asgiref.sync import sync_to_async
from scraper_manager.models import ScraperJob, ScraperConfig
from scraper_manager.config import CONFIG
from scraper_manager.category_taxonomy import normalize_job_categories
from scraper_manager.db_manager import DjangoDBManager
from scraper_manager.scrapers import get_scraper, list_scrapers
from scraper_manager.webhook_notify import dispatch_event

# Setup logging
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Run aviation job scrapers'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'scraper',
            nargs='?',
            type=str,
            help='Scraper name (signature, flygosh, aviationindeed, aap, indigo, aviationjobsearch, goose, linkedin, all)'
        )
        parser.add_argument(
            '--max-jobs',
            type=int,
            help='Maximum number of jobs to scrape'
        )
        parser.add_argument(
            '--max-pages',
            type=int,
            help='Maximum number of pages to scrape'
        )
        parser.add_argument(
            '--list',
            action='store_true',
            help='List all available scrapers'
        )
        parser.add_argument(
            '--job-id',
            type=int,
            help='Pre-created ScraperJob ID'
        )
        parser.add_argument(
            '--job-categories',
            nargs='*',
            help='Optional canonical job categories to keep during filtering',
        )
    
    def handle(self, *args, **options):
        # List scrapers
        if options['list']:
            self.list_available_scrapers()
            return
        
        scraper_name = options.get('scraper')
        if not scraper_name:
            self.stdout.write(self.style.ERROR('Please specify a scraper name or --list'))
            self.stdout.write('Usage: python manage.py run_scraper [scraper_name]')
            enabled_scrapers = [s for s in list_scrapers() if CONFIG['sites'].get(s, {}).get('enabled', False)]
            self.stdout.write(f'Enabled: {", ".join(enabled_scrapers)}, all')
            return
        
        logger.info(f"Starting scraper command: {scraper_name}")
        
        # Run scraper
        if scraper_name == 'all':
            asyncio.run(self.run_all_scrapers(options))
        else:
            asyncio.run(self.run_single_scraper(scraper_name, options))
    
    def list_available_scrapers(self):
        """List all available scrapers"""
        self.stdout.write(self.style.SUCCESS('\n📋 Available Scrapers:\n'))
        
        for scraper_name in list_scrapers():
            site_config = CONFIG['sites'].get(scraper_name, {})
            enabled = site_config.get('enabled', False)
            status = self.style.SUCCESS('✓ Enabled') if enabled else self.style.WARNING('✗ Disabled')
            
            self.stdout.write(f"  • {scraper_name:20s} - {site_config.get('name', 'N/A'):30s} {status}")
        
        self.stdout.write('')
    
    async def run_single_scraper(self, scraper_name: str, options: dict):
        """Run a single scraper"""
        
        logger.info(f"Preparing to run scraper: {scraper_name}")
        
        # Check if scraper exists
        if scraper_name not in list_scrapers():
            error_msg = f'Unknown scraper: {scraper_name}'
            logger.error(error_msg)
            self.stdout.write(self.style.ERROR(error_msg))
            self.stdout.write(f'Available: {", ".join(list_scrapers())}')
            return
        
        # Get config from DB (prioritize DB over code)
        try:
            config, created = await sync_to_async(ScraperConfig.objects.get_or_create)(
                scraper_name=scraper_name,
                defaults={
                    'is_enabled': CONFIG['sites'].get(scraper_name, {}).get('enabled', True),
                    'max_jobs': CONFIG['scrapers'].get(scraper_name, {}).get('max_jobs'),
                    'max_pages': CONFIG['scrapers'].get(scraper_name, {}).get('max_pages')
                }
            )
        except Exception as e:
            logger.warning(f"Could not load config from DB for {scraper_name}: {e}")
            config = None

        # Check if enabled (DB is source of truth)
        if config and not config.is_enabled:
            warning_msg = f'Scraper "{scraper_name}" is disabled in database/admin'
            logger.warning(warning_msg)
            self.stdout.write(self.style.WARNING(warning_msg))
            return
        elif not config:
            # Fallback to code config
            site_config = CONFIG['sites'].get(scraper_name, {})
            if not site_config.get('enabled', False):
                warning_msg = f'Scraper "{scraper_name}" is disabled in config'
                logger.warning(warning_msg)
                self.stdout.write(self.style.WARNING(warning_msg))
                return

        # Determine effective limits
        # Priority: CLI Args > DB Config > Code Defaults (already in DB)
        
        # Max Jobs
        effective_max_jobs = options.get('max_jobs')
        if effective_max_jobs is None and config:
            effective_max_jobs = config.max_jobs
            
        # Max Pages
        effective_max_pages = options.get('max_pages')
        if effective_max_pages is None and config:
            effective_max_pages = config.max_pages
            
        logger.info(f"Effective limits: max_jobs={effective_max_jobs}, max_pages={effective_max_pages}")
        selected_job_categories = normalize_job_categories(options.get('job_categories'))
        
        # Update in-memory config for scrapers that read CONFIG directly (legacy support)
        if effective_max_jobs is not None:
            if scraper_name not in CONFIG['scrapers']: CONFIG['scrapers'][scraper_name] = {}
            CONFIG['scrapers'][scraper_name]['max_jobs'] = effective_max_jobs
        if effective_max_pages is not None:
             if scraper_name not in CONFIG['scrapers']: CONFIG['scrapers'][scraper_name] = {}
             CONFIG['scrapers'][scraper_name]['max_pages'] = effective_max_pages
        
        # Get or Create ScraperJob
        job_id = options.get('job_id')
        if job_id:
            try:
                scraper_job = await sync_to_async(ScraperJob.objects.get)(id=job_id)
                scraper_job.status = 'running'
                scraper_job.pid = os.getpid()
                scraper_job.started_at = timezone.now()
                await sync_to_async(scraper_job.save)()
            except Exception as e:
                logger.error(f"Provided job_id {job_id} not found: {e}")
                job_id = None
        
        if not job_id:
            scraper_job = await sync_to_async(ScraperJob.objects.create)(
                scraper_name=scraper_name,
                status='running',
                pid=os.getpid(),
                started_at=timezone.now(),
                triggered_by='management_command',
                parameters={
                    'max_jobs': options.get('max_jobs'),
                    'max_pages': options.get('max_pages'),
                    'job_categories': selected_job_categories,
                }
            )
        
        logger.info(f"Created ScraperJob with ID: {scraper_job.id}")
        self.stdout.write(self.style.SUCCESS(f'\n🚀 Starting scraper: {scraper_name} (Job ID: {scraper_job.id})'))
        
        try:
            # Initialize database manager
            db_manager = DjangoDBManager()
            logger.info(f"Initialized DjangoDBManager for {scraper_name}")
            
            # Get scraper instance
            CONFIG['job_id'] = scraper_job.id
            CONFIG['selected_job_categories'] = selected_job_categories
            scraper = get_scraper(scraper_name, CONFIG, db_manager=db_manager)
            logger.info(f"Created scraper instance for {scraper_name}")
            
            # Run scraper
            logger.info(f"Starting scraper execution for {scraper_name}")
            jobs = await scraper.run()
            logger.info(f"Scraper execution completed, found {len(jobs)} jobs")
            
            # Update ScraperJob
            scraper_job.status = 'completed'
            scraper_job.completed_at = timezone.now()
            scraper_job.jobs_found = len(jobs)
            
            # Calculate stats from database
            stats = {
                'total': len(jobs),
                'new': sum(1 for j in jobs if j.get('_is_new', False)),
                'updated': sum(1 for j in jobs if not j.get('_is_new', True)),
            }
            
            scraper_job.jobs_new = stats['new']
            scraper_job.jobs_updated = stats['updated']
            scraper_job.jobs_duplicate = stats['total'] - stats['new']
            scraper_job.execution_time = (scraper_job.completed_at - scraper_job.started_at).total_seconds()
            await sync_to_async(scraper_job.save)()
            
            logger.info(f"Updated ScraperJob {scraper_job.id}: "
                       f"found={scraper_job.jobs_found}, new={scraper_job.jobs_new}, "
                       f"updated={scraper_job.jobs_updated}, time={scraper_job.execution_time:.1f}s")
            
            # Update config stats - create default ScraperConfig if missing
            try:
                site_cfg = CONFIG['sites'].get(scraper_name, {})
                defaults = {
                    'is_enabled': site_cfg.get('enabled', True),
                    'max_jobs': site_cfg.get('max_jobs'),
                    'max_pages': site_cfg.get('max_pages'),
                    'description': site_cfg.get('description', ''),
                }
                config, created = await sync_to_async(ScraperConfig.objects.get_or_create)(scraper_name=scraper_name, defaults=defaults)
                await sync_to_async(config.update_stats)(success=True)
                if created:
                    logger.info(f"Created default ScraperConfig for {scraper_name}")
                logger.debug(f"Updated ScraperConfig stats for {scraper_name}")
            except Exception as e:
                logger.warning(f"Failed to update/create ScraperConfig for {scraper_name}: {e}")
            
            self.stdout.write(self.style.SUCCESS(f'\n✓ Scraper completed successfully'))
            self.stdout.write(f'  Jobs found: {scraper_job.jobs_found}')
            self.stdout.write(f'  Jobs new: {scraper_job.jobs_new}')
            self.stdout.write(f'  Jobs updated: {scraper_job.jobs_updated}')
            self.stdout.write(f'  Duration: {scraper_job.execution_time:.1f}s')

            # Fire completion webhook
            await sync_to_async(dispatch_event)('completed', {
                'scraper_name': scraper_name,
                'jobs_found': scraper_job.jobs_found,
                'jobs_new': scraper_job.jobs_new,
                'execution_time': scraper_job.execution_time or 0,
            })
            return 0
            
        except Exception as e:
            logger.error(f"Scraper {scraper_name} failed: {e}", exc_info=True)
            
            scraper_job.status = 'failed'
            scraper_job.completed_at = timezone.now()
            scraper_job.error_message = str(e)
            await sync_to_async(scraper_job.save)()
            
            # Update config stats (ensure config exists)
            try:
                site_cfg = CONFIG['sites'].get(scraper_name, {})
                defaults = {
                    'is_enabled': site_cfg.get('enabled', True),
                    'max_jobs': site_cfg.get('max_jobs'),
                    'max_pages': site_cfg.get('max_pages'),
                    'description': site_cfg.get('description', ''),
                }
                config, created = await sync_to_async(ScraperConfig.objects.get_or_create)(scraper_name=scraper_name, defaults=defaults)
                await sync_to_async(config.update_stats)(success=False)
                if created:
                    logger.info(f"Created default ScraperConfig for {scraper_name} due to failure path")
            except Exception as e2:
                logger.warning(f"Failed to update/create ScraperConfig for {scraper_name}: {e2}")
            
            self.stdout.write(self.style.ERROR(f'\n✗ Scraper failed: {e}'))
            import traceback
            traceback.print_exc()

            # Fire failure webhook
            await sync_to_async(dispatch_event)('failed', {
                'scraper_name': scraper_name,
                'error_message': str(e),
            })
            return 1
    
    async def run_all_scrapers(self, options: dict):
        """Run all enabled scrapers"""
        
        enabled_scrapers = [
            name for name, site in CONFIG['sites'].items()
            if site.get('enabled', False)
        ]
        
        if not enabled_scrapers:
            self.stdout.write(self.style.WARNING('No enabled scrapers found'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'\n🚀 Running {len(enabled_scrapers)} scrapers'))
        
        for scraper_name in enabled_scrapers:
            await self.run_single_scraper(scraper_name, options)
            self.stdout.write('')  # Blank line between scrapers
        
        self.stdout.write(self.style.SUCCESS('\n✓ All scrapers completed'))
