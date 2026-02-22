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
)
def generate_carousel(self, max_fires: int | None = None, force_refresh: bool = False):
    """
    Generate daily carousel thumbnails for active episodes.
    """
    db = SessionLocal()
    try:
        service = ImageryService(db)
        result = service.run_carousel(max_fires=max_fires, force_refresh=force_refresh)
        logger.info("Carousel generation completed: %s", result)
        return {"success": True, **result}
    except Exception as exc:
        db.rollback()
        logger.exception("Carousel generation failed: %s", exc)
        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))
    finally:
        db.close()
