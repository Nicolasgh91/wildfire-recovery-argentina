"""
Semáforo global Redis para limitar concurrencia de requests a Google Earth Engine.

Uso para workers Celery (sync):
    from app.core.gee_semaphore import gee_semaphore

    with gee_semaphore.acquire_sync(timeout=60):
        resultado = gee_service.get_image(...)
"""

import contextlib
import logging
import time
import uuid
from typing import Optional

import redis

from app.core.config import settings

logger = logging.getLogger(__name__)

_SEMAPHORE_KEY = "forestguard:gee_semaphore"
_DEFAULT_MAX_CONCURRENT = 20
_LOCK_TTL_SECONDS = 300  # 5 min max per GEE request


class GEESemaphore:
    """Distributed semaphore based on Redis sorted set with per-entry TTL."""

    def __init__(
        self,
        redis_url: Optional[str] = None,
        max_concurrent: Optional[int] = None,
    ):
        self._redis_url = redis_url or getattr(settings, "REDIS_URL", "redis://redis:6379/0")
        self._max_concurrent = max_concurrent or _DEFAULT_MAX_CONCURRENT
        self._redis: Optional[redis.Redis] = None

    @property
    def _client(self) -> redis.Redis:
        if self._redis is None:
            self._redis = redis.from_url(self._redis_url, decode_responses=True)
        return self._redis

    def _cleanup_expired(self) -> None:
        """Remove expired locks (TTL exceeded)."""
        now = time.time()
        self._client.zremrangebyscore(_SEMAPHORE_KEY, "-inf", now)

    def _try_acquire(self, lock_id: str) -> bool:
        """Attempt to acquire a slot. Returns True if acquired."""
        self._cleanup_expired()
        current_count = self._client.zcard(_SEMAPHORE_KEY)
        if current_count < self._max_concurrent:
            expires_at = time.time() + _LOCK_TTL_SECONDS
            self._client.zadd(_SEMAPHORE_KEY, {lock_id: expires_at})
            return True
        return False

    def _release(self, lock_id: str) -> None:
        """Release a slot."""
        self._client.zrem(_SEMAPHORE_KEY, lock_id)

    @contextlib.contextmanager
    def acquire_sync(self, timeout: int = 60):
        """Synchronous context manager for Celery workers."""
        lock_id = str(uuid.uuid4())
        deadline = time.time() + timeout
        acquired = False

        try:
            while time.time() < deadline:
                if self._try_acquire(lock_id):
                    acquired = True
                    logger.debug("GEE semaphore acquired: %s", lock_id)
                    yield
                    return
                time.sleep(1)

            raise TimeoutError(
                f"No se pudo adquirir slot GEE en {timeout}s. "
                f"Slots ocupados: {self._client.zcard(_SEMAPHORE_KEY)}/{self._max_concurrent}"
            )
        finally:
            if acquired:
                self._release(lock_id)
                logger.debug("GEE semaphore released: %s", lock_id)

    def get_usage(self) -> dict:
        """Return current semaphore usage (for /admin/storage-usage)."""
        self._cleanup_expired()
        current = self._client.zcard(_SEMAPHORE_KEY)
        return {
            "gee_slots_used": current,
            "gee_slots_max": self._max_concurrent,
            "gee_slots_available": self._max_concurrent - current,
        }


# Global singleton
gee_semaphore = GEESemaphore()
