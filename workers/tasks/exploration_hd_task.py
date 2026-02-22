from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from app.db.session import SessionLocal
from app.models.exploration import HdGenerationJob
from app.workers.exploration_hd_worker import run_generation_job
from workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name='workers.tasks.exploration_hd_task.generate_exploration_hd',
    max_retries=3,
)
def generate_exploration_hd(self, job_id: str) -> dict:
    """Generate HD imagery for an exploration job and return its status."""
    try:
        job_uuid = UUID(job_id)
    except ValueError:
        logger.error("exploration_hd_task_invalid_job_id job_id=%s", job_id)
        return {"job_id": job_id, "status": "invalid_id"}

    try:
        run_generation_job(job_uuid)
        status: Optional[str] = None

        db = SessionLocal()
        try:
            job = (
                db.query(HdGenerationJob)
                .filter(HdGenerationJob.id == job_uuid)
                .first()
            )
            status = job.status if job else "not_found"
        finally:
            db.close()

        return {"job_id": job_id, "status": status}
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("exploration_hd_task_failed job_id=%s", job_id)
        raise self.retry(exc=exc, countdown=60)
