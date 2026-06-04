import logging
import socket
import uuid

from celery import chain
from celery import states
from celery import shared_task
from django.db import models
from django.core.management import call_command
from django.utils import timezone

from jobs.models import Job

from .category_taxonomy import normalize_job_categories
from .config import CONFIG
from .models import ACTIVE_JOB_STATUSES, ScraperConfig, ScraperJob
from .services.job_monitoring import finalize_stale_active_jobs
from .services.job_events import publish_job_event
from .services.job_url_checks import check_job_url


logger = logging.getLogger(__name__)


@shared_task(bind=True, name="scraper_manager.worker_ping")
def worker_ping(self):
    return {
        "task_id": self.request.id,
        "worker": socket.gethostname(),
        "timestamp": timezone.now().isoformat(),
        "status": "ok",
    }


@shared_task(bind=True, name="scraper_manager.queue_scraper_sequence_task")
def queue_scraper_sequence_task(
    self,
    scraper_names,
    triggered_by="",
    max_jobs=None,
    max_pages=None,
    job_categories=None,
):
    normalized_categories = normalize_job_categories(job_categories)
    config_map = {cfg.scraper_name: cfg for cfg in ScraperConfig.objects.all()}
    queued_jobs = []
    queued_job_ids = []
    signatures = []
    skipped = {
        "disabled": [],
        "already_running": [],
        "dispatch_failed": [],
    }
    total_requested = len(scraper_names or [])

    for position, scraper_name in enumerate(scraper_names or [], start=1):
        finalize_stale_active_jobs(scraper_name=scraper_name, source="sequence_planner")

        scraper_config = config_map.get(scraper_name)
        is_enabled = (
            scraper_config.is_enabled
            if scraper_config
            else CONFIG["sites"].get(scraper_name, {}).get("enabled", False)
        )
        if not is_enabled:
            skipped["disabled"].append(scraper_name)
            continue

        active_count = ScraperJob.objects.filter(
            scraper_name=scraper_name,
            status__in=ACTIVE_JOB_STATUSES,
        ).count()
        if active_count > 0:
            skipped["already_running"].append(
                {
                    "scraper_name": scraper_name,
                    "active_jobs": active_count,
                }
            )
            continue

        child_task_id = uuid.uuid4().hex
        scraper_job = ScraperJob.objects.create(
            scraper_name=scraper_name,
            status="queued",
            task_id=child_task_id,
            progress_message="Queued in start-all sequence",
            triggered_by=triggered_by,
            parameters={
                "max_jobs": max_jobs,
                "max_pages": max_pages,
                "job_categories": normalized_categories,
                "triggered_from": "start_all",
                "sequence_task_id": self.request.id,
                "sequence_position": position,
                "sequence_size": total_requested,
                "celery_task_id": child_task_id,
            },
        )

        publish_job_event(
            "job.queued",
            scraper_job,
            extra={
                "source": "sequence_planner",
                "sequence_position": position,
                "sequence_size": total_requested,
            },
        )
        queued_job_ids.append(scraper_job.pk)
        queued_jobs.append(
            {
                "job_id": str(scraper_job.pk),
                "scraper_name": scraper_name,
                "status": "queued",
                "task_id": child_task_id,
            }
        )
        signatures.append(
            run_scraper_task.si(
                scraper_name=scraper_name,
                job_id=str(scraper_job.pk),
                max_jobs=max_jobs,
                max_pages=max_pages,
                job_categories=normalized_categories,
            ).set(task_id=child_task_id)
        )

    if not signatures:
        return {
            "queued_count": 0,
            "jobs": [],
            "skipped": skipped,
        }

    try:
        chain(*signatures).apply_async()
    except Exception as exc:
        logger.exception("Failed to queue start-all sequence")
        for scraper_job in ScraperJob.objects.filter(pk__in=queued_job_ids):
            scraper_job.status = "failed"
            scraper_job.progress_message = "Sequence planning failed"
            scraper_job.failure_code = exc.__class__.__name__
            scraper_job.failure_context = {
                **(scraper_job.failure_context or {}),
                "source": "sequence_planner",
                "message": str(exc),
            }
            scraper_job.error_message = f"Sequence planning failed: {exc}"
            scraper_job.completed_at = timezone.now()
            scraper_job.save(
                update_fields=[
                    "status",
                    "progress_message",
                    "failure_code",
                    "failure_context",
                    "error_message",
                    "completed_at",
                ]
            )
            publish_job_event(
                "job.failed", scraper_job, extra={"source": "sequence_planner"}
            )
        raise

    return {
        "queued_count": len(queued_jobs),
        "jobs": queued_jobs,
        "skipped": skipped,
        "sequence_task_id": self.request.id,
    }


@shared_task(bind=True, name="scraper_manager.bulk_check_job_url_status_task")
def bulk_check_job_url_status_task(
    self,
    search="",
    status_filter="",
    source_filter="",
    max_checks=200,
    skip_verified=True,
    only_scraped=True,
):
    queryset = Job.objects.all()
    if search:
        queryset = queryset.filter(
            models.Q(title__icontains=search)
            | models.Q(company__icontains=search)
            | models.Q(location__icontains=search)
            | models.Q(source__icontains=search)
            | models.Q(operation_type__icontains=search)
            | models.Q(job_category__icontains=search)
        )
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    if source_filter:
        queryset = queryset.filter(source=source_filter)
    if only_scraped:
        queryset = queryset.exclude(source__isnull=True).exclude(source="")

    jobs = list(queryset.order_by("-retrieved_date", "-created_at")[:max_checks])
    results = {
        "checked": 0,
        "skipped_verified": 0,
        "skipped_no_url": 0,
        "failed_requests": 0,
        "status_changed": 0,
        "closed_detected": 0,
        "total_candidates": len(jobs),
    }

    for job in jobs:
        if skip_verified and job.is_verified:
            results["skipped_verified"] += 1
            continue

        check_payload = check_job_url(job)
        if check_payload["result"] == "skipped_no_url":
            results["skipped_no_url"] += 1
            continue
        if check_payload["result"] == "request_failed":
            results["failed_requests"] += 1
            continue

        results["checked"] += 1
        if check_payload["status_changed"]:
            results["status_changed"] += 1
        if check_payload["status"] == "closed":
            results["closed_detected"] += 1

    return {
        "message": "Bulk URL validation completed",
        "filters": {
            "q": search,
            "status": status_filter,
            "source": source_filter,
            "only_scraped": only_scraped,
            "skip_verified": skip_verified,
            "max_checks": max_checks,
        },
        "results": results,
    }


@shared_task(bind=True, name="scraper_manager.reconcile_stale_jobs_task")
def reconcile_stale_jobs_task(self):
    reconciled = finalize_stale_active_jobs(source="beat_monitor")
    return {
        "reconciled": reconciled,
        "timestamp": timezone.now().isoformat(),
    }


@shared_task(bind=True, name="scraper_manager.run_scraper_task")
def run_scraper_task(
    self, scraper_name, job_id, max_jobs=None, max_pages=None, job_categories=None
):
    job = ScraperJob.objects.filter(pk=job_id).first()
    attempt_count = int(getattr(self.request, "retries", 0)) + 1
    worker_name = socket.gethostname()

    if job is not None:
        parameters = {**(job.parameters or {}), "celery_task_id": self.request.id}
        update_fields = [
            "task_id",
            "worker_name",
            "heartbeat_at",
            "progress",
            "progress_message",
            "attempt_count",
            "parameters",
        ]

        job.task_id = self.request.id or ""
        job.worker_name = worker_name
        job.heartbeat_at = timezone.now()
        job.progress = max(job.progress or 0, 5)
        job.progress_message = "Worker accepted task"
        job.attempt_count = max(job.attempt_count or 0, attempt_count)
        job.parameters = parameters

        if job.status in {"pending", "queued", "retrying"}:
            job.status = "running"
            update_fields.append("status")
        if job.started_at is None:
            job.started_at = timezone.now()
            update_fields.append("started_at")

        job.save(update_fields=sorted(set(update_fields)))
        publish_job_event(
            "job.started", job, extra={"source": "celery", "worker": worker_name}
        )

    try:
        call_command(
            "run_scraper",
            scraper_name,
            job_id=job_id,
            max_jobs=max_jobs,
            max_pages=max_pages,
            job_categories=job_categories or None,
        )
    except Exception as exc:
        logger.exception(
            "Celery wrapper failed for scraper %s job %s", scraper_name, job_id
        )
        job = ScraperJob.objects.filter(pk=job_id).first()
        if job is not None:
            was_cancelled = bool(job.cancel_requested_at) or job.status == "cancelling"
            job.status = "cancelled" if was_cancelled else "failed"
            job.error_message = (
                "Cancelled by user"
                if was_cancelled
                else f"Celery task wrapper failed: {exc}"
            )
            job.failure_code = "cancelled" if was_cancelled else exc.__class__.__name__
            job.failure_context = {
                **(job.failure_context or {}),
                "source": "celery_wrapper",
                "message": str(exc),
            }
            job.completed_at = timezone.now()
            job.heartbeat_at = timezone.now()
            job.progress_message = (
                "Cancelled by user" if was_cancelled else "Worker task failed"
            )
            job.save(
                update_fields=[
                    "status",
                    "error_message",
                    "failure_code",
                    "failure_context",
                    "completed_at",
                    "heartbeat_at",
                    "progress_message",
                ]
            )
            publish_job_event(
                "job.cancelled" if was_cancelled else "job.failed",
                job,
                extra={"source": "celery_wrapper"},
            )

        self.update_state(
            state=states.FAILURE,
            meta={"job_id": str(job_id), "scraper_name": scraper_name},
        )
        raise

    job = ScraperJob.objects.filter(pk=job_id).first()
    if job is None:
        return {
            "job_id": str(job_id),
            "scraper_name": scraper_name,
            "status": "missing",
        }

    job.heartbeat_at = timezone.now()
    job.save(update_fields=["heartbeat_at"])

    return {
        "job_id": str(job.pk),
        "scraper_name": scraper_name,
        "status": job.status,
        "jobs_found": job.jobs_found,
        "jobs_new": job.jobs_new,
        "jobs_updated": job.jobs_updated,
        "jobs_duplicate": job.jobs_duplicate,
    }
