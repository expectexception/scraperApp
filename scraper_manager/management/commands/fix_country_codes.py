"""
Re-derive country_code from location for all jobs using the fixed longest-match
algorithm. Fixes cases like "Papua New Guinea" → GN (wrong) → PG (correct).
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from jobs.models import Job
from scraper_manager.location_manager import LocationManager


class Command(BaseCommand):
    help = "Re-derive country_code from location and fix mismatches in the DB"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Show changes without persisting")
        parser.add_argument("--wrong-code", type=str, help="Only fix jobs with this stored country_code (e.g. GN)")
        parser.add_argument("--limit", type=int, default=0, help="Max jobs to process")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        wrong_code = options.get("wrong_code")
        limit = options.get("limit", 0)

        qs = Job.objects.exclude(location__isnull=True).exclude(location="")
        if wrong_code:
            qs = qs.filter(country_code__iexact=wrong_code)
        if limit:
            qs = qs[:limit]

        total = qs.count()
        self.stdout.write(f"Checking {total} jobs (wrong_code={wrong_code}, dry_run={dry_run})")

        fixed = 0
        skipped = 0

        for job in qs.iterator(chunk_size=500):
            correct_cc = LocationManager.extract_country_code(job.location)
            if correct_cc and correct_cc != job.country_code:
                self.stdout.write(
                    f"  FIX [{job.id}] {job.location!r}: {job.country_code!r} → {correct_cc!r}"
                )
                if not dry_run:
                    Job.objects.filter(pk=job.pk).update(country_code=correct_cc)
                fixed += 1
            else:
                skipped += 1

        self.stdout.write(self.style.SUCCESS(
            f"Done: fixed={fixed}, unchanged={skipped}, dry_run={dry_run}"
        ))
