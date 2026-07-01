from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.db import models
from jobs.models import Job
from scraper_manager.db_manager import DjangoDBManager
from asgiref.sync import async_to_sync
import logging
import asyncio

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
            default=0,
            help="Only check jobs last checked older than this many days (default 0 checks all)",
        )
        parser.add_argument(
            "--dry-run", action="store_true", help="Do not persist changes"
        )
        parser.add_argument(
            "--concurrency",
            type=int,
            default=10,
            help="Max concurrent requests (default 10)",
        )

    def handle(self, *args, **options):
        source = options.get("source")
        limit = options.get("limit", 0)
        age_days = options.get("age_days", 0)
        dry = options.get("dry_run", False)
        concurrency = options.get("concurrency", 10)

        dbm = DjangoDBManager()

        qs = Job.objects.defer("raw_json").filter(status__in=["new", "active"])
        if age_days > 0:
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
            f"Processing {total} active/unverified jobs (source={source}, age_days={age_days}, dry_run={dry})"
        )

        updated = 0
        errors = 0
        done_count = 0

        async def verify_jobs_concurrently(jobs_list):
            sem = asyncio.Semaphore(concurrency)

            async def verify_one(job):
                async with sem:
                    try:
                        is_active, reason = await dbm.check_job_active(
                            job.url, job_obj=job
                        )
                        return job, is_active, reason
                    except Exception as e:
                        return job, True, f"exception:{str(e)}"

            tasks = [verify_one(j) for j in jobs_list]
            results = []
            for coro in asyncio.as_completed(tasks):
                result = await coro
                results.append(result)
            return results

        # Run concurrent checks
        results = async_to_sync(verify_jobs_concurrently)(jobs)

        # Process results sequentially to avoid SQLite locking issues
        for job, is_active, reason in results:
            done_count += 1
            if done_count % 50 == 0 or done_count == total:
                self.stdout.write(f"Progress: {done_count}/{total} (closed={updated}, errors={errors})")
            if "exception:" in reason:
                errors += 1
                self.stderr.write(f"Error checking {job.url}: {reason}")
                continue

            try:
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
                logger.exception("Error saving job status %s", job.url)

        self.stdout.write(
            self.style.SUCCESS(
                f"Processing complete: processed={total}, updated={updated}, errors={errors}"
            )
        )

