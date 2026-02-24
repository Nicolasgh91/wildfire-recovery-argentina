"""
Carousel task (UC-F08).
"""

import logging

from app.db.session import SessionLocal
from app.services.imagery_service import ImageryService
from workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="workers.tasks.carousel_task.generate_carousel",
    queue="analysis",
    max_retries=3,
    retry_backoff=True,
    retry_jitter=True,
)
def generate_carousel(self, max_fires: int | None = None, force_refresh: bool = False):
    """
    Generate daily carousel thumbnails for active episodes.
    Guaranteed single execution at a time via Redis distributed lock.
    """
    from app.services.redis_service import redis_client

    lock_key = "carousel:generation_lock"
    # Timeout after 30 mins to avoid infinite stale locks if worker crashes hard.
    acquired = redis_client.set(lock_key, "locked", nx=True, ex=1800)

    if not acquired:
        logger.info("Carousel generation already running. Skipping this invocation.")
        return {"success": False, "reason": "lock_acquired_by_another_worker"}

    db = SessionLocal()
    try:
        service = ImageryService(db)
        result = service.run_carousel(max_fires=max_fires, force_refresh=force_refresh)
        logger.info("Carousel generation completed: %s", result)
        return {"success": True, **result}
    except Exception as exc:
        db.rollback()
        logger.error("Carousel generation failed: %s", exc, exc_info=True)
        raise self.retry(exc=exc)
    finally:
        redis_client.delete(lock_key)
        db.close()
