from __future__ import annotations

import os
from typing import Mapping, Optional

from app.core.config import settings

DEFAULT_REDIS_URL = "redis://localhost:6379/0"


def _clean_url(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    candidate = value.strip()
    return candidate or None


def _first_defined(*values: Optional[str]) -> str:
    for value in values:
        cleaned = _clean_url(value)
        if cleaned is not None:
            return cleaned
    return DEFAULT_REDIS_URL


def resolve_celery_broker_url(
    environ: Optional[Mapping[str, str]] = None,
) -> str:
    env = environ or os.environ
    return _first_defined(
        env.get("CELERY_BROKER_URL"),
        settings.CELERY_BROKER_URL,
        env.get("REDIS_URL"),
        settings.REDIS_URL,
        DEFAULT_REDIS_URL,
    )


def resolve_celery_result_backend(
    environ: Optional[Mapping[str, str]] = None,
) -> str:
    env = environ or os.environ
    return _first_defined(
        env.get("CELERY_RESULT_BACKEND"),
        settings.CELERY_RESULT_BACKEND,
        resolve_celery_broker_url(env),
    )
