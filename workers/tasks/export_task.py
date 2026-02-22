"""Celery task for async fire event exports (PERF-006).

Large exports (> EXPORT_SYNC_LIMIT records) are offloaded to this task
so the API thread is freed immediately. The caller receives a task ID
and can poll for completion.
"""
import logging

from workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="workers.tasks.export_task.export_fires_async",
    max_retries=2,
    default_retry_delay=30,
    queue="analysis",
)
def export_fires_async(self, export_params: dict) -> dict:
    """Generate a fire export file asynchronously.

    Parameters
    ----------
    export_params : dict
        Keys: query_filters (dict), export_format (str),
              filters_applied (dict), max_records (int | None),
              user_id (str | None).

    Returns
    -------
    dict with keys: status, file_url | error
    """
    from app.db.session import SessionLocal
    from app.services.export_service import ExportService

    db = SessionLocal()
    try:
        service = ExportService(db)

        logger.info(
            "Async export started task_id=%s format=%s",
            self.request.id,
            export_params.get("export_format"),
        )

        # Re-build query from filters (simplified — the real implementation
        # would reconstruct the SQLAlchemy query from serialised filters).
        result = service.export_fires_from_params(export_params)

        logger.info(
            "Async export completed task_id=%s records=%s",
            self.request.id,
            result.get("records_exported", 0),
        )
        return {"status": "completed", **result}

    except Exception as exc:
        logger.error("Async export failed task_id=%s error=%s", self.request.id, exc)
        raise self.retry(exc=exc)
    finally:
        db.close()
