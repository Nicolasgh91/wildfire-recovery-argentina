"""
Task Celery para generar PDF tras completar job HD.

Se ejecuta como tarea independiente encadenada al job HD.
Si falla, el job HD permanece en estado 'ready' (las imágenes están disponibles).
El PDF es un complemento, no un requisito.
"""
from __future__ import annotations

import logging
import time
from typing import Optional
from uuid import UUID

from sqlalchemy import text

from app.db.session import SessionLocal
from app.models.exploration import (
    HdGenerationJob,
    InvestigationAsset,
    InvestigationItem,
    UserInvestigation,
)
from app.services.pdf_generation_service import PdfGenerationService
from app.services.storage_service import BUCKETS, StorageService
from workers.celery_app import celery_app

logger = logging.getLogger(__name__)


def _read_param(db, param_key: str, default):
    """Read a system_parameter value using raw SQL (no ORM model)."""
    row = db.execute(
        text("SELECT param_value FROM system_parameters WHERE param_key = :key"),
        {"key": param_key},
    ).fetchone()
    if row and row[0]:
        return row[0].get("value", default)
    return default


@celery_app.task(
    bind=True,
    name="workers.tasks.pdf_generation_task.generate_pdf_for_job",
    max_retries=2,
    default_retry_delay=30,
)
def generate_pdf_for_job(self, job_id: str) -> dict:
    """
    Generate PDF from completed HD job results.

    Flow:
    1. Load job and HD results from DB.
    2. Generate PDF in memory with PdfGenerationService.
    3. Upload to storage.
    4. Update job.results with pdf_url, pdf_sha256, pdf_status.

    If it fails, the HD job stays available with status 'ready'.
    """
    try:
        job_uuid = UUID(job_id)
    except ValueError:
        logger.error("pdf_task_invalid_job_id job_id=%s", job_id)
        return {"status": "error", "detail": "Invalid job ID"}

    db = SessionLocal()
    pdf_service = PdfGenerationService()

    try:
        # 1. Load job
        job = (
            db.query(HdGenerationJob)
            .filter(HdGenerationJob.id == job_uuid)
            .first()
        )

        if not job:
            logger.error("pdf_task_job_not_found job_id=%s", job_id)
            return {"status": "error", "detail": "Job not found"}

        if job.status != "ready":
            logger.warning(
                "pdf_task_job_not_ready job_id=%s status=%s", job_id, job.status
            )
            return {"status": "skipped", "detail": f"Job status is {job.status}"}

        # 2. Read parameters from system_parameters
        max_images = _read_param(db, "pdf_max_embedded_images", 6)
        image_dpi = _read_param(db, "pdf_image_dpi", 150)
        max_size_mb = _read_param(db, "pdf_max_size_mb", 20)

        # 3. Build HD results dict from investigation items/assets
        investigation_id = str(job.investigation_id)
        items = (
            db.query(InvestigationItem)
            .filter(InvestigationItem.investigation_id == job.investigation_id)
            .order_by(InvestigationItem.target_date.asc())
            .all()
        )

        images_list = []
        for item in items:
            asset = (
                db.query(InvestigationAsset)
                .filter(InvestigationAsset.investigation_item_id == item.id)
                .first()
            )
            images_list.append(
                {
                    "band": (item.visualization_params or {}).get("vis_type", "RGB"),
                    "target_date": item.target_date.strftime("%Y-%m-%d")
                    if item.target_date
                    else "N/A",
                    "status": item.status,
                    "sensor": item.sensor or "sentinel-2",
                    "local_path": None,  # HD assets are in cloud storage, not local
                }
            )

        hd_results = {"images": images_list}

        # Get investigation title
        investigation = (
            db.query(UserInvestigation)
            .filter(UserInvestigation.id == job.investigation_id)
            .first()
        )
        title = investigation.title if investigation else None

        # 4. Generate PDF in memory
        pdf_bytes, sha256 = pdf_service.generate_exploration_pdf(
            investigation_id=investigation_id,
            job_id=job_id,
            hd_results=hd_results,
            investigation_title=title,
            max_images=max_images,
            image_dpi=image_dpi,
        )

        # 5. Validate content
        if not pdf_bytes or not pdf_bytes[:5] == b"%PDF-":
            raise ValueError("Generated PDF is invalid (does not start with %PDF-)")

        # 6. Check max size
        actual_size_mb = len(pdf_bytes) / (1024 * 1024)
        if actual_size_mb > max_size_mb:
            logger.warning(
                "PDF exceeds limit: %.1f MB > %s MB. Regenerating without images.",
                actual_size_mb,
                max_size_mb,
            )
            pdf_bytes, sha256 = pdf_service.generate_exploration_pdf(
                investigation_id=investigation_id,
                job_id=job_id,
                hd_results=hd_results,
                investigation_title=title,
                max_images=0,
            )

        # 7. Upload to storage with retry
        storage = StorageService()
        object_key = f"explorations/{investigation_id}/{job_id}.pdf"
        upload_result = _upload_with_retry(
            storage=storage,
            object_key=object_key,
            file_bytes=pdf_bytes,
            content_type="application/pdf",
        )

        # 8. Update job with PDF results
        results = dict(job.results) if job.results else {}
        results["pdf_url"] = upload_result.url
        results["pdf_sha256"] = sha256
        results["pdf_status"] = "generated"
        results["pdf_size_bytes"] = len(pdf_bytes)
        job.results = results
        db.commit()

        logger.info(
            "pdf_generated job_id=%s size=%d sha256=%s...",
            job_id,
            len(pdf_bytes),
            sha256[:12],
        )

        return {
            "status": "generated",
            "pdf_url": upload_result.url,
            "sha256": sha256,
            "size_bytes": len(pdf_bytes),
        }

    except Exception as e:
        logger.error("pdf_task_failed job_id=%s error=%s", job_id, e, exc_info=True)

        # Mark PDF status as failed without affecting HD job
        try:
            if job:
                results = dict(job.results) if job.results else {}
                results["pdf_status"] = "failed"
                results["pdf_error"] = str(e)[:200]
                job.results = results
                db.commit()
        except Exception:
            pass

        # Retry if attempts remain
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)

        return {"status": "failed", "detail": str(e)[:200]}

    finally:
        db.close()


def _upload_with_retry(
    storage: StorageService,
    object_key: str,
    file_bytes: bytes,
    content_type: str,
    max_retries: int = 3,
):
    """Upload file to storage with exponential backoff retry."""
    last_error: Optional[Exception] = None
    for attempt in range(max_retries):
        try:
            result = storage.upload_bytes(
                data=file_bytes,
                key=object_key,
                bucket=BUCKETS.get("reports", "forestguard-reports"),
                content_type=content_type,
            )
            if result.success:
                return result
            raise RuntimeError(f"Upload failed: {result.error}")
        except Exception as e:
            last_error = e
            wait_time = (2**attempt) * 2  # 2s, 4s, 8s
            logger.warning(
                "Storage upload attempt %d/%d failed: %s. Retrying in %ds...",
                attempt + 1,
                max_retries,
                e,
                wait_time,
            )
            time.sleep(wait_time)

    raise RuntimeError(f"Upload failed after {max_retries} attempts: {last_error}")
