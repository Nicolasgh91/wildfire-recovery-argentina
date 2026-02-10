"""
Closure report task (UC-F09).
"""

import logging

from app.db.session import SessionLocal
from app.services.closure_report_service import ClosureReportService
from workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="workers.tasks.closure_report_task.generate_closure_reports",
    queue="analysis",
    max_retries=3,
)
def generate_closure_reports(self, max_fires: int | None = None):
    """
    Generate closure reports for eligible extinguished fires.
    """
    db = SessionLocal()
    try:
        service = ClosureReportService(db)
        result = service.run(max_fires=max_fires)
        logger.info("Closure report worker completed: %s", result)
        return {"success": True, **result}
    except Exception as exc:
        db.rollback()
        logger.exception("Closure report worker failed: %s", exc)
        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))
    finally:
        db.close()
