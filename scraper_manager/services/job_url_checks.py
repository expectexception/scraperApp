import requests
from django.utils import timezone


DEFAULT_JOB_CHECK_TIMEOUT = 8
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/91.0.4472.124 Safari/537.36"
    )
}
CLOSED_KEYWORDS = [
    "position no longer available",
    "job is closed",
    "no longer accepting applications",
    "this job has expired",
    "position has been filled",
    "job not found",
    "page not found",
    "opportunity has passed",
    "no longer active",
]


def check_job_url(job, timeout: int = DEFAULT_JOB_CHECK_TIMEOUT) -> dict:
    if not job.url:
        return {
            "result": "skipped_no_url",
            "error": "Job has no URL to check",
            "status_changed": False,
            "status": job.status,
        }

    previous_status = job.status

    try:
        response = requests.get(
            job.url, headers=REQUEST_HEADERS, timeout=timeout, allow_redirects=True
        )
    except requests.RequestException as exc:
        return {
            "result": "request_failed",
            "error": str(exc),
            "status_changed": False,
            "status": job.status,
        }

    result = "active"
    should_mark_closed = False
    if response.status_code in [404, 410]:
        should_mark_closed = True
        result = "closed_status_code"
    else:
        content_lower = response.text.lower()
        if any(keyword in content_lower for keyword in CLOSED_KEYWORDS):
            should_mark_closed = True
            result = "closed_keyword_match"
        else:
            result = (
                "active"
                if previous_status != "closed"
                else "was_closed_now_seems_active"
            )

    if should_mark_closed:
        job.status = "closed"

    job.last_checked = timezone.now()
    update_fields = ["last_checked"]
    if job.status != previous_status:
        update_fields.append("status")
    job.save(update_fields=update_fields)

    return {
        "result": result,
        "error": None,
        "status_changed": job.status != previous_status,
        "status": job.status,
        "last_checked": job.last_checked,
    }
