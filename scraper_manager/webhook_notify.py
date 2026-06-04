"""
Webhook notification utility for AeroOps scraper events.
Supports: ntfy.sh, Slack Webhooks, and custom HTTP POST endpoints.
"""

import json
import logging
import threading
from datetime import datetime

logger = logging.getLogger(__name__)


def _fire_webhook(url: str, payload: dict, provider: str):
    """Internal — fires a webhook in a background thread so it never blocks the scraper."""
    try:
        import urllib.request

        data = json.dumps(payload).encode()
        headers = {"Content-Type": "application/json"}

        if provider == "ntfy":
            # ntfy expects plain text or JSON; we POST the message as the body
            msg = payload.get("message", "AeroOps Alert")
            headers = {
                "Title": payload.get("title", "AeroOps"),
                "Tags": payload.get("tags", "white_check_mark"),
                "Priority": payload.get("priority", "default"),
                "Content-Type": "text/plain",
            }
            data = msg.encode()

        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=8) as resp:
            logger.info(f"[webhook] fired → {url} status={resp.status}")
    except Exception as e:
        logger.warning(f"[webhook] failed to fire {url}: {e}")


def dispatch_event(event: str, context: dict):
    """
    Dispatch a scraper lifecycle event to all matching active webhooks.

    Args:
        event:   'completed' | 'failed' | 'cancelled'
        context: dict with keys: scraper_name, jobs_new, jobs_found,
                 execution_time, error_message
    """
    try:
        from scraper_manager.models import WebhookConfig

        hooks = WebhookConfig.objects.filter(
            is_active=True,
        ).filter(
            # match 'all' or the specific event
            on_event__in=["all", event]
        )

        if not hooks.exists():
            return

        scraper = context.get("scraper_name", "?")
        new_jobs = context.get("jobs_new", 0)
        duration = context.get("execution_time")
        err_msg = context.get("error_message", "")
        ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

        if event == "completed":
            icon = "✅"
            title = f"AeroOps — {scraper.upper()} Completed"
            message = (
                f"{icon} Scraper: {scraper.upper()}\n"
                f"New jobs: {new_jobs}\n"
                f"Duration: {duration:.0f}s\n"
                f"Time: {ts}"
            )
            tags = "white_check_mark"
            priority = "default"
        elif event == "failed":
            icon = "❌"
            title = f"AeroOps — {scraper.upper()} FAILED"
            message = (
                f"{icon} Scraper: {scraper.upper()}\nError: {err_msg[:200]}\nTime: {ts}"
            )
            tags = "x,rotating_light"
            priority = "high"
        else:
            icon = "⏹"
            title = f"AeroOps — {scraper.upper()} {event.title()}"
            message = f"{icon} {scraper.upper()} — {event} at {ts}"
            tags = "information_source"
            priority = "low"

        base_payload = {
            "title": title,
            "message": message,
            "tags": tags,
            "priority": priority,
            "event": event,
            "scraper": scraper,
            "new_jobs": new_jobs,
            "ts": ts,
        }

        for hook in hooks:
            t = threading.Thread(
                target=_fire_webhook,
                args=(hook.url, base_payload, hook.provider),
                daemon=True,
            )
            t.start()

    except Exception as e:
        logger.warning(f"[webhook] dispatch_event error: {e}")
