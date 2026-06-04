"""
Django management command to clean up expired/old jobs.
Usage: python manage.py cleanup_jobs [--days N] [--dry-run]
"""

import logging
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from jobs.models import Job
from scraper_manager.models import ScraperJob

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Mark jobs older than N days as expired and optionally purge them"

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=90,
            help="Jobs older than this many days are considered expired (default: 90)",
        )
        parser.add_argument(
            "--purge-scraper-history",
            type=int,
            default=30,
            metavar="DAYS",
            help="Purge ScraperJob records older than N days (default: 30)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be deleted/updated without actually doing it",
        )
        parser.add_argument(
            "--delete",
            action="store_true",
            help="Hard-delete expired jobs instead of marking them expired",
        )

    def handle(self, *args, **options):
        days = options["days"]
        history_days = options["purge_scraper_history"]
        dry_run = options["dry_run"]
        hard_delete = options["delete"]
        cutoff = timezone.now() - timedelta(days=days)
        hist_cutoff = timezone.now() - timedelta(days=history_days)

        prefix = "[DRY-RUN] " if dry_run else ""

        # ── 1. Handle old jobs ────────────────────────────────────────────
        old_jobs = Job.objects.filter(retrieved_date__lt=cutoff).exclude(
            status="expired"
        )

        count = old_jobs.count()
        self.stdout.write(
            self.style.WARNING(f"{prefix}Found {count} jobs older than {days} days.")
        )

        if count > 0 and not dry_run:
            if hard_delete:
                old_jobs.delete()
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Hard-deleted {count} expired jobs.")
                )
            else:
                updated = old_jobs.update(status="expired")
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Marked {updated} jobs as expired.")
                )
        elif dry_run:
            sample = list(old_jobs.values_list("title", "company")[:5])
            for title, company in sample:
                self.stdout.write(f"  • [{company}] {title[:60]}")

        # ── 2. Purge stale ScraperJob history ─────────────────────────────
        old_records = ScraperJob.objects.filter(
            created_at__lt=hist_cutoff,
            status__in=["completed", "failed", "cancelled"],
        )
        rec_count = old_records.count()
        self.stdout.write(
            self.style.WARNING(
                f"{prefix}Found {rec_count} scraper history records older than {history_days} days."
            )
        )
        if rec_count > 0 and not dry_run:
            old_records.delete()
            self.stdout.write(
                self.style.SUCCESS(f"✓ Purged {rec_count} old scraper history records.")
            )

        self.stdout.write(self.style.SUCCESS("\n✅ Cleanup complete."))
        logger.info(
            f"cleanup_jobs: jobs_expired={count}, history_purged={rec_count}, dry_run={dry_run}"
        )
