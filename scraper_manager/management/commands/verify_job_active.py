from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.db import models
from jobs.models import Job
from scraper_manager.db_manager import DjangoDBManager
from asgiref.sync import async_to_sync
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Verify active jobs by checking their page status and mark them closed if the job is no longer available."

    def add_arguments(self, parser):
        parser.add_argument("--source", type=str, help="Source to verify (optional)")
        parser.add_argument(
            "--limit", type=int, default=0, help="Limit the number of jobs to process"
        )
        parser.add_argument(
            "--age-days",
            type=int,
            default=7,
            help="Only check jobs last checked older than this many days",
        )
        parser.add_argument(
            "--dry-run", action="store_true", help="Do not persist changes"
        )

    def handle(self, *args, **options):
        source = options.get("source")
        limit = options.get("limit", 0)
        age_days = options.get("age_days", 7)
        dry = options.get("dry_run", False)

        dbm = DjangoDBManager()

        qs = Job.objects.filter(status__in=["new", "active"], posted_by__isnull=True)
        cutoff = timezone.now() - timezone.timedelta(days=age_days)
        qs = qs.filter(
            models.Q(last_checked__lt=cutoff) | models.Q(last_checked__isnull=True)
        )
        if source:
            qs = qs.filter(source__iexact=source)
        qs = qs.order_by("last_checked")
        if limit and limit > 0:
            qs = qs[:limit]

        jobs = list(qs)
        total = len(jobs)
        self.stdout.write(
            f"Processing {total} jobs with status new/active and last_checked older than {age_days} days (source={source}, dry_run={dry})"
        )

        updated = 0
        errors = 0
        for job in jobs:
            try:
                is_active, reason = async_to_sync(dbm.check_job_active)(
                    job.url, job_obj=job
                )
                job.last_checked = timezone.now()
                if not is_active:
                    if not dry:
                        with transaction.atomic():
                            dbm.mark_job_closed(job.url, reason)
                    updated += 1
                    self.stdout.write(
                        f"Job closed: {job.url} [{job.id}] reason={reason}"
                    )
                else:
                    if not dry:
                        job.save(update_fields=["last_checked"])
                    self.stdout.write(f"Job still active: {job.url} [{job.id}]")
            except Exception:
                errors += 1
                logger.exception("Error verifying job %s", job.url)

        self.stdout.write(
            self.style.SUCCESS(
                f"Processing complete: processed={total}, updated={updated}, errors={errors}"
            )
        )
