"""
Django management command to run scrapers
Usage: python manage.py run_scraper [scraper_name] [options]
"""

import asyncio
import os
import sys
import time
import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from asgiref.sync import sync_to_async
from scraper_manager.models import ScraperJob, ScraperConfig
from scraper_manager.services.job_events import publish_job_event
from scraper_manager.config import CONFIG
from scraper_manager.category_taxonomy import normalize_job_categories
from scraper_manager.db_manager import DjangoDBManager
from scraper_manager.scrapers import get_scraper, list_scrapers
from scraper_manager.webhook_notify import dispatch_event

# Setup logging
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Run aviation job scrapers"

    def add_arguments(self, parser):
        parser.add_argument(
            "scraper",
            nargs="?",
            type=str,
            help="Scraper name (signature, flygosh, aviationindeed, aap, indigo, aviationjobsearch, goose, linkedin, all)",
        )
        parser.add_argument(
            "--max-jobs", type=int, help="Maximum number of jobs to scrape"
        )
        parser.add_argument(
            "--max-pages", type=int, help="Maximum number of pages to scrape"
        )
        parser.add_argument(
            "--list", action="store_true", help="List all available scrapers"
        )
        parser.add_argument("--job-id", type=int, help="Pre-created ScraperJob ID")
        parser.add_argument(
            "--job-categories",
            nargs="*",
            help="Optional canonical job categories to keep during filtering",
        )
        parser.add_argument(
            "--no-db",
            action="store_true",
            help="Run without database connection (for testing)",
        )
        parser.add_argument(
            "--quiet", action="store_true", help="Suppress individual scraper output"
        )

    def handle(self, *args, **options):
        # List scrapers
        if options["list"]:
            self.list_available_scrapers()
            return

        scraper_name = options.get("scraper")
        if not scraper_name:
            self.stdout.write(
                self.style.ERROR("Please specify a scraper name or --list")
            )
            self.stdout.write("Usage: python manage.py run_scraper [scraper_name]")
            enabled_scrapers = [
                s
                for s in list_scrapers()
                if CONFIG["sites"].get(s, {}).get("enabled", False)
            ]
            self.stdout.write(f"Enabled: {', '.join(enabled_scrapers)}, all")
            return

        logger.info(f"Starting scraper command: {scraper_name}")

        # Run scraper
        if scraper_name == "all":
            asyncio.run(self.run_all_scrapers(options))
        else:
            asyncio.run(self.run_single_scraper(scraper_name, options))

    def list_available_scrapers(self):
        """List all available scrapers"""
        self.stdout.write(self.style.SUCCESS("\n📋 Available Scrapers:\n"))

        for scraper_name in list_scrapers():
            site_config = CONFIG["sites"].get(scraper_name, {})
            enabled = site_config.get("enabled", False)
            status = (
                self.style.SUCCESS("✓ Enabled")
                if enabled
                else self.style.WARNING("✗ Disabled")
            )

            self.stdout.write(
                f"  • {scraper_name:20s} - {site_config.get('name', 'N/A'):30s} {status}"
            )

        self.stdout.write("")

    async def run_single_scraper(
        self, scraper_name: str, options: dict, quiet: bool = False
    ):
        """Run a single scraper"""

        if not quiet:
            logger.info(f"Preparing to run scraper: {scraper_name}")

        # Check if scraper exists
        if scraper_name not in list_scrapers():
            error_msg = f"Unknown scraper: {scraper_name}"
            if not quiet:
                logger.error(error_msg)
                self.stdout.write(self.style.ERROR(error_msg))
                self.stdout.write(f"Available: {', '.join(list_scrapers())}")
            return 1, None

        # Get config from DB (prioritize DB over code)
        try:
            config, created = await sync_to_async(ScraperConfig.objects.get_or_create)(
                scraper_name=scraper_name,
                defaults={
                    "is_enabled": CONFIG["sites"]
                    .get(scraper_name, {})
                    .get("enabled", True),
                    "max_jobs": CONFIG["scrapers"]
                    .get(scraper_name, {})
                    .get("max_jobs"),
                    "max_pages": CONFIG["scrapers"]
                    .get(scraper_name, {})
                    .get("max_pages"),
                },
            )
        except Exception as e:
            logger.warning(f"Could not load config from DB for {scraper_name}: {e}")
            config = None

        # Check if enabled (DB is source of truth)
        if config and not config.is_enabled:
            warning_msg = f'Scraper "{scraper_name}" is disabled in database/admin'
            if not quiet:
                logger.warning(warning_msg)
                self.stdout.write(self.style.WARNING(warning_msg))
            return 1, None
        elif not config:
            # Fallback to code config
            site_config = CONFIG["sites"].get(scraper_name, {})
            if not site_config.get("enabled", False):
                warning_msg = f'Scraper "{scraper_name}" is disabled in config'
                if not quiet:
                    logger.warning(warning_msg)
                    self.stdout.write(self.style.WARNING(warning_msg))
                return 1, None

        # Determine effective limits
        # Priority: CLI Args > DB Config > Code Defaults (already in DB)

        # Max Jobs
        effective_max_jobs = options.get("max_jobs")
        if effective_max_jobs is None and config:
            effective_max_jobs = config.max_jobs

        # Max Pages
        effective_max_pages = options.get("max_pages")
        if effective_max_pages is None and config:
            effective_max_pages = config.max_pages

        logger.info(
            f"Effective limits: max_jobs={effective_max_jobs}, max_pages={effective_max_pages}"
        )
        selected_job_categories = normalize_job_categories(
            options.get("job_categories")
        )

        # Update in-memory config for scrapers that read CONFIG directly (legacy support)
        if effective_max_jobs is not None:
            if scraper_name not in CONFIG["scrapers"]:
                CONFIG["scrapers"][scraper_name] = {}
            CONFIG["scrapers"][scraper_name]["max_jobs"] = effective_max_jobs
        if effective_max_pages is not None:
            if scraper_name not in CONFIG["scrapers"]:
                CONFIG["scrapers"][scraper_name] = {}
            CONFIG["scrapers"][scraper_name]["max_pages"] = effective_max_pages

        # Get or Create ScraperJob
        no_db = options.get("no_db", False)
        scraper_job = None

        if not no_db:
            job_id = options.get("job_id")
            if job_id:
                try:
                    scraper_job = await sync_to_async(ScraperJob.objects.get)(id=job_id)
                    scraper_job.status = "running"
                    scraper_job.pid = os.getpid()
                    scraper_job.started_at = scraper_job.started_at or timezone.now()
                    scraper_job.heartbeat_at = timezone.now()
                    scraper_job.progress = max(scraper_job.progress or 0, 10)
                    scraper_job.progress_message = "Scraper process running"
                    await sync_to_async(scraper_job.save)(
                        update_fields=[
                            "status",
                            "pid",
                            "started_at",
                            "heartbeat_at",
                            "progress",
                            "progress_message",
                        ]
                    )
                    await sync_to_async(publish_job_event)(
                        "job.progress",
                        scraper_job,
                        extra={"message": "Scraper process started"},
                    )
                except Exception as e:
                    logger.error(f"Provided job_id {job_id} not found: {e}")
                    job_id = None

            if not job_id:
                scraper_job = await sync_to_async(ScraperJob.objects.create)(
                    scraper_name=scraper_name,
                    status="running",
                    pid=os.getpid(),
                    started_at=timezone.now(),
                    heartbeat_at=timezone.now(),
                    progress=10,
                    progress_message="Scraper process running",
                    triggered_by="management_command",
                    parameters={
                        "max_jobs": options.get("max_jobs"),
                        "max_pages": options.get("max_pages"),
                        "job_categories": selected_job_categories,
                    },
                )
                await sync_to_async(publish_job_event)(
                    "job.started", scraper_job, extra={"source": "management_command"}
                )

            if not quiet:
                logger.info(f"Created ScraperJob with ID: {scraper_job.id}")
                self.stdout.write(
                    self.style.SUCCESS(
                        f"\n🚀 Starting scraper: {scraper_name} (Job ID: {scraper_job.id})"
                    )
                )
        else:
            if not quiet:
                self.stdout.write(
                    self.style.WARNING(
                        f"\n🚀 Starting scraper: {scraper_name} (NO-DB MODE)"
                    )
                )

            # Create a mock object with attributes for compatibility
            class MockJob:
                def __init__(self):
                    self.id = 0
                    self.status = "running"
                    self.jobs_found = 0
                    self.jobs_new = 0
                    self.jobs_updated = 0
                    self.jobs_duplicate = 0
                    self.execution_time = 0.0
                    self.error_message = ""
                    self.started_at = timezone.now()
                    self.completed_at = timezone.now()

                def save(self):
                    pass

            scraper_job = MockJob()

        original_stdout = sys.stdout
        original_stderr = sys.stderr
        if quiet:
            _devnull = open(os.devnull, "w")
            sys.stdout = _devnull
            sys.stderr = _devnull

        def _restore_streams():
            if quiet:
                sys.stdout = original_stdout
                sys.stderr = original_stderr
                try:
                    _devnull.close()
                except Exception:
                    pass

        try:
            # Initialize database manager
            if not no_db:
                db_manager = DjangoDBManager()
                logger.info(f"Initialized DjangoDBManager for {scraper_name}")
            else:
                db_manager = None
                logger.info("Skipping DjangoDBManager (no-db mode)")

            # Get scraper instance
            CONFIG["job_id"] = scraper_job.id
            CONFIG["selected_job_categories"] = selected_job_categories
            scraper = get_scraper(scraper_name, CONFIG, db_manager=db_manager)
            logger.info(f"Created scraper instance for {scraper_name}")

            # Run scraper
            logger.info(f"Starting scraper execution for {scraper_name}")
            jobs = await scraper.run()
            # Scraper execution completed
            logger.info(f"Scraper execution completed, found {len(jobs)} jobs")

            if quiet:
                _restore_streams()
            if not no_db:
                # Update ScraperJob
                scraper_job.status = "completed"
                scraper_job.completed_at = timezone.now()
                scraper_job.heartbeat_at = timezone.now()
                scraper_job.jobs_found = len(jobs)

                # Calculate stats from database
                stats = {
                    "total": len(jobs),
                    "new": sum(1 for j in jobs if j.get("_is_new", False)),
                    "updated": sum(1 for j in jobs if not j.get("_is_new", True)),
                }

                scraper_job.jobs_new = stats["new"]
                scraper_job.jobs_updated = stats["updated"]
                scraper_job.jobs_duplicate = stats["total"] - stats["new"]
                scraper_job.execution_time = (
                    scraper_job.completed_at - scraper_job.started_at
                ).total_seconds()
                scraper_job.progress = 100
                scraper_job.progress_message = "Completed successfully"
                await sync_to_async(scraper_job.save)()
                await sync_to_async(publish_job_event)(
                    "job.completed", scraper_job, extra={"source": "management_command"}
                )
            else:
                # Output jobs summary in no-db mode
                self.stdout.write(
                    self.style.SUCCESS(f"Found {len(jobs)} jobs in no-db mode")
                )
                for i, job in enumerate(jobs[:5], 1):
                    self.stdout.write(
                        f"  [{i}] {job.get('title')} @ {job.get('company')}"
                    )
                if len(jobs) > 5:
                    self.stdout.write(f"  ... and {len(jobs) - 5} more")

                # Update scraper_job for final summary
                scraper_job.jobs_found = len(jobs)
                scraper_job.jobs_new = len(
                    jobs
                )  # In no-db mode, assume all are new for reporting
                scraper_job.execution_time = (
                    timezone.now() - scraper_job.started_at
                ).total_seconds()

            logger.info(
                f"Updated ScraperJob {scraper_job.id}: "
                f"found={scraper_job.jobs_found}, new={scraper_job.jobs_new}, "
                f"updated={scraper_job.jobs_updated}, time={scraper_job.execution_time:.1f}s"
            )

            # Update config stats - create default ScraperConfig if missing
            if not no_db:
                try:
                    site_cfg = CONFIG["sites"].get(scraper_name, {})
                    defaults = {
                        "is_enabled": site_cfg.get("enabled", True),
                        "max_jobs": site_cfg.get("max_jobs"),
                        "max_pages": site_cfg.get("max_pages"),
                        "description": site_cfg.get("description", ""),
                    }
                    config, created = await sync_to_async(
                        ScraperConfig.objects.get_or_create
                    )(scraper_name=scraper_name, defaults=defaults)
                    await sync_to_async(config.update_stats)(success=True)
                    if created:
                        logger.info(f"Created default ScraperConfig for {scraper_name}")
                    logger.debug(f"Updated ScraperConfig stats for {scraper_name}")
                except Exception as e:
                    logger.warning(
                        f"Failed to update/create ScraperConfig for {scraper_name}: {e}"
                    )

            if not quiet:
                self.stdout.write(
                    self.style.SUCCESS("\n✓ Scraper completed successfully")
                )
                self.stdout.write(f"  Jobs found: {scraper_job.jobs_found}")
                self.stdout.write(f"  Jobs new: {scraper_job.jobs_new}")
                self.stdout.write(f"  Jobs updated: {scraper_job.jobs_updated}")
                self.stdout.write(f"  Duration: {scraper_job.execution_time:.1f}s")

            # Fire completion webhook
            await sync_to_async(dispatch_event)(
                "completed",
                {
                    "scraper_name": scraper_name,
                    "jobs_found": scraper_job.jobs_found,
                    "jobs_new": scraper_job.jobs_new,
                    "execution_time": scraper_job.execution_time or 0,
                },
            )
            return 0, scraper_job

        except Exception as e:
            _restore_streams()
            logger.error(f"Scraper {scraper_name} failed: {e}", exc_info=True)

            if not no_db:
                was_cancelled = bool(scraper_job.cancel_requested_at)
                scraper_job.status = "cancelled" if was_cancelled else "failed"
                scraper_job.completed_at = timezone.now()
                scraper_job.heartbeat_at = timezone.now()
                scraper_job.error_message = (
                    "Cancelled by user" if was_cancelled else str(e)
                )
                scraper_job.failure_code = (
                    "cancelled" if was_cancelled else e.__class__.__name__
                )
                scraper_job.failure_context = {
                    **(scraper_job.failure_context or {}),
                    "source": "management_command",
                    "message": str(e),
                }
                scraper_job.progress_message = (
                    "Cancelled by user" if was_cancelled else "Execution failed"
                )
                await sync_to_async(scraper_job.save)()
                await sync_to_async(publish_job_event)(
                    "job.cancelled" if was_cancelled else "job.failed",
                    scraper_job,
                    extra={"source": "management_command"},
                )

            # Update config stats (ensure config exists)
            if not no_db:
                try:
                    site_cfg = CONFIG["sites"].get(scraper_name, {})
                    defaults = {
                        "is_enabled": site_cfg.get("enabled", True),
                        "max_jobs": site_cfg.get("max_jobs"),
                        "max_pages": site_cfg.get("max_pages"),
                        "description": site_cfg.get("description", ""),
                    }
                    config, created = await sync_to_async(
                        ScraperConfig.objects.get_or_create
                    )(scraper_name=scraper_name, defaults=defaults)
                    await sync_to_async(config.update_stats)(success=False)
                    if created:
                        logger.info(
                            f"Created default ScraperConfig for {scraper_name} due to failure path"
                        )
                except Exception as e2:
                    logger.warning(
                        f"Failed to update/create ScraperConfig for {scraper_name}: {e2}"
                    )

            if not quiet:
                self.stdout.write(self.style.ERROR(f"\n✗ Scraper failed: {e}"))
                import traceback

                traceback.print_exc()

            # Fire failure webhook
            await sync_to_async(dispatch_event)(
                "failed",
                {
                    "scraper_name": scraper_name,
                    "error_message": str(e),
                },
            )
            return 1, scraper_job

    async def run_all_scrapers(self, options: dict):
        """Run all enabled scrapers"""
        from ...scrapers import list_scrapers as list_implemented
        import sys

        implemented = set(list_implemented())

        enabled_scrapers = [
            name
            for name, site in CONFIG["sites"].items()
            if site.get("enabled", False) and name in implemented
        ]

        skipped = [
            name
            for name, site in CONFIG["sites"].items()
            if site.get("enabled", False) and name not in implemented
        ]

        if not enabled_scrapers:
            self.stdout.write(
                self.style.WARNING("No enabled scrapers with implementations found")
            )
            return

        # Turn off noisy logging
        logging.disable(logging.CRITICAL)

        total = len(enabled_scrapers)
        self.stdout.write(
            self.style.SUCCESS(
                f"\n🚀 Running {total} scrapers ({len(skipped)} skipped — no implementation)\n"
            )
        )

        total_found = 0
        total_new = 0
        total_dupes = 0
        errors = 0

        for i, scraper_name in enumerate(enabled_scrapers, 1):
            # Show current scraper being run
            sys.stdout.write(
                f"\r⏳ [{i}/{total}] Running: {scraper_name:<25s}                    "
            )
            sys.stdout.flush()

            t0 = time.time()
            try:
                code, job_stats = await self.run_single_scraper(
                    scraper_name, options, quiet=True
                )
                elapsed = time.time() - t0
                found = getattr(job_stats, "jobs_found", 0) if job_stats else 0
                new = getattr(job_stats, "jobs_new", 0) if job_stats else 0
                dupes = getattr(job_stats, "jobs_duplicate", 0) if job_stats else 0

                if code == 0 and job_stats:
                    total_found += found
                    total_new += new
                    total_dupes += dupes

                # Print completed line then progress
                result_icon = "✓" if code == 0 else "✗"
                self.stdout.write(
                    f"  {result_icon} [{i}/{total}] {scraper_name:<25s} "
                    f"found={found} new={new} dupes={dupes}  ({elapsed:.1f}s)"
                )
            except Exception as e:
                elapsed = time.time() - t0
                errors += 1
                self.stdout.write(
                    self.style.ERROR(
                        f"  ✗ [{i}/{total}] {scraper_name:<25s} ERROR: {e}  ({elapsed:.1f}s)"
                    )
                )

            # Running totals line
            sys.stdout.write(
                f"\r⏳ Progress: [{i}/{total}] | Found: {total_found} | New: {total_new} | Dupes: {total_dupes}          "
            )
            sys.stdout.flush()

        self.stdout.write(
            self.style.SUCCESS(
                f"\n\n✓ All {total} scrapers completed! ({errors} errors)"
            )
        )
        self.stdout.write(f"  Total Jobs Found: {total_found}")
        self.stdout.write(f"  Total New Jobs:   {total_new}")
        self.stdout.write(f"  Total Duplicates: {total_dupes}\n")
        if skipped:
            self.stdout.write(
                self.style.WARNING(f"  Skipped (no impl): {', '.join(skipped)}\n")
            )
