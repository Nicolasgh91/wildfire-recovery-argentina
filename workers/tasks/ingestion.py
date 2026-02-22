"""
Ingestion tasks for NASA FIRMS data.
"""

import logging
from datetime import datetime, timezone

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name="workers.tasks.ingestion.download_firms_daily",
    queue="ingestion",
    max_retries=3,
)
def download_firms_daily(self, days: int = 2, dry_run: bool = False):
    """
    Execute real incremental FIRMS ingestion pipeline.

    Returns:
        dict with ingestion metrics and basic traceability fields.
    """
    try:
        logger.info("Starting FIRMS ingestion (days=%s, dry_run=%s)", days, dry_run)

        # Lazy import keeps worker module import-time lightweight.
        from scripts.load_firms_incremental import run_incremental_pipeline

        pipeline_result = run_incremental_pipeline(days=days, dry_run=dry_run)
        if not isinstance(pipeline_result, dict):
            raise RuntimeError(
                "run_incremental_pipeline must return a dict with ingestion metrics"
            )

        result = {
            "success": bool(pipeline_result.get("success", True)),
            "records_inserted": int(pipeline_result.get("records_inserted", 0)),
            "duplicates_found": int(pipeline_result.get("duplicates_found", 0)),
            "total_filtered": int(pipeline_result.get("total_filtered", 0)),
            "events_created": int(pipeline_result.get("events_created", 0)),
            "areas_calculated": int(pipeline_result.get("areas_calculated", 0)),
            "intersections": int(pipeline_result.get("intersections", 0)),
            "dry_run": bool(dry_run),
            "source": "scripts.load_firms_incremental.run_incremental_pipeline",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        logger.info(f"FIRMS ingestion finished: {result}")
        return result

    except Exception as exc:
        logger.error("FIRMS ingestion failed: %s", exc)
        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))


@shared_task(
    name="workers.tasks.ingestion.process_firms_batch",
    bind=True,
)
def process_firms_batch(self, csv_data, batch_id):
    """
    Process a FIRMS batch payload.

    This task remains a lightweight placeholder for future per-batch logic.
    """
    try:
        logger.info("Processing FIRMS batch %s", batch_id)

        processed = {
            "batch_id": batch_id,
            "total_records": 0,
            "valid_records": 0,
            "filtered_out": 0,
        }

        return processed

    except Exception as exc:
        logger.error("Failed processing FIRMS batch %s: %s", batch_id, exc)
        raise self.retry(exc=exc, countdown=30)
