import logging
from datetime import timedelta

import psutil
from celery import current_app
from django.utils import timezone

from scraper_manager.models import ACTIVE_JOB_STATUSES, ScraperJob

from .job_events import publish_job_event


logger = logging.getLogger(__name__)
ACTIVE_JOB_STALE_TIMEOUT = timedelta(minutes=15)


def active_job_reference_time(job: ScraperJob):
    return job.heartbeat_at or job.started_at or job.created_at


def get_task_runtime_state(job: ScraperJob) -> str | None:
    task_id = job.task_id or (job.parameters or {}).get("celery_task_id")
    if not task_id:
        return None

    try:
        return current_app.AsyncResult(task_id).state
    except Exception:
        return None


def is_job_stale(job: ScraperJob) -> bool:
    reference_time = active_job_reference_time(job)
    if reference_time is None:
        return False

    now = timezone.now()
    if now - reference_time <= ACTIVE_JOB_STALE_TIMEOUT:
        return False

    if job.pid:
        try:
            if psutil.pid_exists(job.pid):
                return False
        except Exception:
            pass

    task_state = get_task_runtime_state(job)
    if task_state in {"PENDING", "RECEIVED", "STARTED", "RETRY"}:
        return False

    return True


def describe_job_liveness(job: ScraperJob) -> dict:
    reference_time = active_job_reference_time(job)
    now = timezone.now()
    heartbeat_age_seconds = None
    if reference_time is not None:
        heartbeat_age_seconds = max((now - reference_time).total_seconds(), 0.0)

    pid_alive = None
    if job.pid:
        try:
            pid_alive = psutil.pid_exists(job.pid)
        except Exception:
            pid_alive = None

    return {
        "is_stale": is_job_stale(job),
        "task_state": get_task_runtime_state(job),
        "pid_alive": pid_alive,
        "last_seen_at": reference_time.isoformat() if reference_time else None,
        "heartbeat_age_seconds": heartbeat_age_seconds,
        "stale_timeout_seconds": ACTIVE_JOB_STALE_TIMEOUT.total_seconds(),
    }


def finalize_stale_active_jobs(
    scraper_name: str | None = None, source: str = "job_monitor"
) -> int:
    queryset = ScraperJob.objects.filter(status__in=ACTIVE_JOB_STATUSES)
    if scraper_name:
        queryset = queryset.filter(scraper_name=scraper_name)

    updated = 0
    for job in queryset:
        if not is_job_stale(job):
            continue

        reference_time = active_job_reference_time(job)
        job.status = "failed"
        job.completed_at = timezone.now()
        job.heartbeat_at = job.heartbeat_at or reference_time
        job.failure_code = "stale_job"
        job.failure_context = {
            **(job.failure_context or {}),
            "source": source,
            "reason": "active job exceeded stale timeout without a live worker identity",
            "reference_time": reference_time.isoformat() if reference_time else None,
        }
        job.error_message = "Job marked failed after stale active state reconciliation."
        job.progress_message = "Marked stale by monitor reconciliation"
        if job.started_at and job.completed_at:
            job.execution_time = (job.completed_at - job.started_at).total_seconds()
        job.save(
            update_fields=[
                "status",
                "completed_at",
                "heartbeat_at",
                "failure_code",
                "failure_context",
                "error_message",
                "progress_message",
                "execution_time",
            ]
        )
        publish_job_event(
            "job.failed", job, extra={"source": source, "reason": "stale_job"}
        )
        updated += 1

    if updated:
        logger.info("Reconciled %s stale scraper job(s)", updated)

    return updated
