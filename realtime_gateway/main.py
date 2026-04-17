import json
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "scraper_service.settings")

import django

django.setup()

from django.conf import settings
from django.core import signing
from django.utils import timezone
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from redis.asyncio import from_url as redis_from_url

from scraper_manager.auth import TOKEN_TTL_SECONDS, validate_dashboard_token


app = FastAPI(title="AeroOps Realtime Gateway")
allowed_origins = [
    getattr(settings, "FRONTEND_URL", "http://localhost:8501"),
    "http://localhost:5173",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)


def _event_channel() -> str:
    return getattr(settings, "SCRAPER_EVENT_CHANNEL", "scraper.events")


@app.get("/health")
async def health():
    redis_client = redis_from_url(getattr(settings, "REDIS_URL", "redis://127.0.0.1:6379/0"), decode_responses=True)
    redis_ok = False
    try:
        redis_ok = bool(await redis_client.ping())
    finally:
        await redis_client.aclose()

    return {
        "status": "ok" if redis_ok else "degraded",
        "redis": redis_ok,
        "channel": _event_channel(),
    }


@app.get("/events")
async def events(request: Request, token: str = Query(...)):
    try:
        username = validate_dashboard_token(token, max_age=TOKEN_TTL_SECONDS)
    except signing.SignatureExpired as exc:
        raise HTTPException(status_code=401, detail="Token expired") from exc
    except signing.BadSignature as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc

    channel = _event_channel()

    async def event_stream():
        redis_client = redis_from_url(getattr(settings, "REDIS_URL", "redis://127.0.0.1:6379/0"), decode_responses=True)
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(channel)

        try:
            yield f"data: {json.dumps({'type': 'connected', 'timestamp': timezone.now().isoformat(), 'channel': channel, 'user': username})}\n\n"

            while True:
                if await request.is_disconnected():
                    break

                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=15.0)
                if message and message.get("type") == "message":
                    data = message.get("data", "")
                    if isinstance(data, bytes):
                        data = data.decode("utf-8")
                    yield f"data: {data}\n\n"
                    continue

                yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': timezone.now().isoformat()})}\n\n"
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()
            await redis_client.aclose()

    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(event_stream(), media_type="text/event-stream", headers=headers)