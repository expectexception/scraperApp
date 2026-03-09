from django.core.management.base import BaseCommand
from django.utils import timezone
from scraper_manager.config import CONFIG
from scraper_manager.logging_config import setup_logging
import logging
import asyncio
import sys
import os
from datetime import datetime


class Command(BaseCommand):
    help = 'Run all enabled scrapers with comprehensive logging'

    def add_arguments(self, parser):
        parser.add_argument(
            '--max-jobs',
            type=int,
            default=None,
            help='Maximum jobs per scraper (default: from config)',
        )
        parser.add_argument(
            '--max-pages',
            type=int,
            default=None,
            help='Maximum pages per scraper (default: from config)',
        )
        parser.add_argument(
            '--log-level',
            choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
            default='INFO',
            help='Logging level (default: INFO)',
        )
        parser.add_argument(
            '--scrapers',
            nargs='*',
            help='Specific scrapers to run (default: all enabled)',
        )

    def handle(self, *args, **options):
        # Setup logging
        logger = setup_logging()
        log_level = getattr(logging, options['log_level'].upper())
        logger.setLevel(log_level)

        # Set console handler level too
        for handler in logger.handlers:
            if hasattr(handler, 'setLevel'):
                handler.setLevel(log_level)

        start_time = timezone.now()
        logger.info("=" * 80)
        logger.info(f"🚀 STARTING ALL SCRAPERS - {start_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        logger.info("=" * 80)

        # Get enabled scrapers
        all_scrapers = CONFIG.get('sites', {})
        if options['scrapers']:
            enabled_scrapers = [s for s in options['scrapers'] if s in all_scrapers]
            if not enabled_scrapers:
                logger.error(f"None of the specified scrapers found: {options['scrapers']}")
                return
        else:
            enabled_scrapers = [
                name for name, site in all_scrapers.items()
                if site.get('enabled', False)
            ]

        if not enabled_scrapers:
            logger.warning("No enabled scrapers found in configuration")
            return

        logger.info(f"📋 Will run {len(enabled_scrapers)} scrapers: {', '.join(enabled_scrapers)}")

        # Run scrapers
        results = []
        total_jobs_found = 0
        total_new_jobs = 0
        successful_runs = 0

        for scraper_name in enabled_scrapers:
            scraper_start = timezone.now()
            logger.info(f"\\n🔄 Starting scraper: {scraper_name} at {scraper_start.strftime('%H:%M:%S')}")

            try:
                # Import and run scraper
                from django.core.management import call_command
                from io import StringIO

                # Capture output
                output_buffer = StringIO()

                # Build arguments
                call_args = [scraper_name]
                call_kwargs = {
                    'stdout': output_buffer,
                    'stderr': output_buffer,
                }

                if options['max_jobs']:
                    call_kwargs['max_jobs'] = options['max_jobs']

                # Run the scraper
                result_code = call_command('run_scraper', *call_args, **call_kwargs)

                # Parse output for statistics
                output = output_buffer.getvalue()
                logger.info(f"Scraper {scraper_name} output:\\n{output}")

                # Extract statistics from output
                jobs_found = 0
                jobs_new = 0
                jobs_updated = 0

                for line in output.split('\\n'):
                    line = line.strip()
                    if 'Jobs found:' in line and 'Jobs new:' in line:
                        # Parse summary line
                        try:
                            parts = line.split()
                            jobs_found = int(parts[2])
                            jobs_new = int(parts[5])
                            jobs_updated = int(parts[8]) if len(parts) > 8 else 0
                        except (ValueError, IndexError):
                            pass
                    elif '✅ Database updated:' in line:
                        # Alternative parsing
                        try:
                            parts = line.split()
                            if 'new=' in line:
                                jobs_new = int(line.split('new=')[1].split(',')[0])
                            if 'updated=' in line:
                                jobs_updated = int(line.split('updated=')[1].split(',')[0])
                        except (ValueError, IndexError):
                            pass

                scraper_end = timezone.now()
                duration = (scraper_end - scraper_start).total_seconds()

                result = {
                    'scraper_name': scraper_name,
                    'status': 'success' if result_code == 0 else 'failed',
                    'jobs_found': jobs_found,
                    'jobs_new': jobs_new,
                    'jobs_updated': jobs_updated,
                    'duration': duration,
                    'output': output,
                }

                results.append(result)

                if result_code == 0:
                    successful_runs += 1
                    total_jobs_found += jobs_found
                    total_new_jobs += jobs_new
                    logger.info(f"✅ {scraper_name} completed successfully in {duration:.1f}s - {jobs_found} jobs ({jobs_new} new)")
                else:
                    logger.error(f"❌ {scraper_name} failed with code {result_code} in {duration:.1f}s")

            except Exception as e:
                scraper_end = timezone.now()
                duration = (scraper_end - scraper_start).total_seconds()
                logger.error(f"💥 {scraper_name} crashed after {duration:.1f}s: {e}")

                results.append({
                    'scraper_name': scraper_name,
                    'status': 'crashed',
                    'error': str(e),
                    'duration': duration,
                })

        # Summary
        end_time = timezone.now()
        total_duration = (end_time - start_time).total_seconds()

        logger.info("\\n" + "=" * 80)
        logger.info("📊 SCRAPING SESSION SUMMARY")
        logger.info("=" * 80)
        logger.info(f"⏱️  Total duration: {total_duration:.1f} seconds")
        logger.info(f"🔄 Scrapers run: {len(enabled_scrapers)}")
        logger.info(f"✅ Successful: {successful_runs}")
        logger.info(f"❌ Failed: {len(enabled_scrapers) - successful_runs}")
        logger.info(f"📄 Total jobs found: {total_jobs_found}")
        logger.info(f"🆕 Total new jobs: {total_new_jobs}")
        logger.info(f"🏁 Completed at: {end_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        logger.info("=" * 80)

        # Detailed results
        logger.info("\\n📋 DETAILED RESULTS:")
        for result in results:
            status_emoji = "✅" if result['status'] == 'success' else "❌" if result['status'] == 'failed' else "💥"
            logger.info(f"  {status_emoji} {result['scraper_name']}: {result.get('jobs_found', 0)} jobs in {result.get('duration', 0):.1f}s")

        # Exit with appropriate code
        if successful_runs == len(enabled_scrapers):
            logger.info("🎉 All scrapers completed successfully!")
            sys.exit(0)
        elif successful_runs > 0:
            logger.warning(f"⚠️  {successful_runs}/{len(enabled_scrapers)} scrapers completed successfully")
            sys.exit(1)
        else:
            logger.error("💥 All scrapers failed!")
            sys.exit(2)