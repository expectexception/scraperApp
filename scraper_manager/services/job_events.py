import json
import logging

import redis
from django.conf import settings
from django.utils import timezone


logger = logging.getLogger(__name__)


def _isoformat(value):
    return value.isoformat() if value else None


def serialize_job(job) -> dict:
    parameters = dict(job.parameters or {})
    failure_context = dict(job.failure_context or {})
    task_id = job.task_id or parameters.get("celery_task_id") or ""

    return {
        "id": str(job.pk),
        "scraper_name": job.scraper_name,
        "status": job.status,
        "task_id": task_id,
        "worker_name": job.worker_name,
        "pid": job.pid,
        "progress": job.progress,
        "progress_message": job.progress_message,
        "jobs_found": job.jobs_found,
        "jobs_new": job.jobs_new,
        "jobs_updated": job.jobs_updated,
        "jobs_duplicate": job.jobs_duplicate,
        "attempt_count": job.attempt_count,
        "triggered_by": job.triggered_by,
        "created_at": _isoformat(job.created_at),
        "started_at": _isoformat(job.started_at),
        "completed_at": _isoformat(job.completed_at),
        "heartbeat_at": _isoformat(job.heartbeat_at),
        "cancel_requested_at": _isoformat(job.cancel_requested_at),
        "execution_time": job.execution_time,
        "error_message": job.error_message,
        "failure_code": job.failure_code,
        "failure_context": failure_context,
        "parameters": parameters,
    }


def build_job_event(event: str, job, extra: dict | None = None) -> dict:
    return {
        "type": "job_event",
        "event": event,
        "timestamp": timezone.now().isoformat(),
        "job": serialize_job(job),
        "extra": extra or {},
    }


def publish_job_event(event: str, job, extra: dict | None = None) -> dict | None:
    redis_url = getattr(settings, "REDIS_URL", "")
    if not redis_url:
        return None

    payload = build_job_event(event, job, extra=extra)
    channel = getattr(settings, "SCRAPER_EVENT_CHANNEL", "scraper.events")
    client = None

    try:
        client = redis.from_url(redis_url, decode_responses=True)
        client.publish(channel, json.dumps(payload))
        return payload
    except Exception as exc:
        logger.warning(
            "Unable to publish scraper event %s for job %s: %s",
            event,
            getattr(job, "pk", "unknown"),
            exc,
        )
        return None
    finally:
        if client is not None:
            try:
                client.close()
            except Exception:
                pass
