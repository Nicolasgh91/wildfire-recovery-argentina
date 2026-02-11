from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict

import redis

from app.core.alerts import send_alert
logger = logging.getLogger(__name__)


def _redis_url() -> str:
    return (
        os.getenv("CELERY_BROKER_URL")
        or os.getenv("REDIS_URL")
        or "redis://redis:6379/0"
    )


def _dlq_key() -> str:
    return os.getenv("WORKERS_DLQ_KEY", "forestguard:dlq")


def _dlq_max_length() -> int:
    raw = os.getenv("WORKERS_DLQ_MAX_LENGTH", "1000")
    try:
        return max(int(raw), 0)
    except (TypeError, ValueError):
        return 1000


def enqueue_failure(payload: Dict[str, Any]) -> None:
    try:
        client = redis.from_url(_redis_url(), socket_timeout=5)
        data = json.dumps(payload, default=str, ensure_ascii=True)
        key = _dlq_key()
        max_len = _dlq_max_length()
        pipe = client.pipeline()
        pipe.lpush(key, data)
        if max_len:
            pipe.ltrim(key, 0, max_len - 1)
        pipe.execute()
        send_alert(
            subject="DLQ enqueue",
            body=f"DLQ payload enqueued (key={key}). Payload keys: {', '.join(payload.keys())}",
        )
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.exception("dlq_enqueue_failed error=%s", exc)
