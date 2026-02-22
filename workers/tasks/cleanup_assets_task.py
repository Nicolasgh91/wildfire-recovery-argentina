"""
Job programado para limpiar assets expirados de storage.

Política de retención (desde system_parameters):
- Assets HD: hd_asset_retention_days (default 7)
- PDFs: pdf_retention_days (default 90)
- Thumbnails: no se eliminan (persistentes)

Schedule: diario a las 04:00 UTC
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from app.db.session import SessionLocal
from app.models.exploration import InvestigationAsset
from app.services.storage_service import BUCKETS, StorageService
from workers.celery_app import celery_app

logger = logging.getLogger(__name__)


def _read_param(db, param_key: str, default):
    """Read a system_parameter value using raw SQL."""
    row = db.execute(
        text("SELECT param_value FROM system_parameters WHERE param_key = :key"),
        {"key": param_key},
    ).fetchone()
    if row and row[0]:
        return row[0].get("value", default)
    return default


@celery_app.task(
    name="workers.tasks.cleanup_assets_task.cleanup_expired_assets",
)
def cleanup_expired_assets() -> dict:
    """Delete expired assets from storage and update DB."""
    db = SessionLocal()
    storage = StorageService()

    try:
        # Read retention parameters
        hd_retention_days = _read_param(db, "hd_asset_retention_days", 7)
        pdf_retention_days = _read_param(db, "pdf_retention_days", 90)

        now = datetime.now(timezone.utc)
        hd_cutoff = now - timedelta(days=hd_retention_days)

        # Find expired HD assets
        expired_hd = (
            db.query(InvestigationAsset)
            .filter(InvestigationAsset.generated_at < hd_cutoff)
            .all()
        )

        hd_deleted = 0
        hd_errors = 0
        for asset in expired_hd:
            try:
                storage.delete_object(
                    key=asset.gcs_path,
                    bucket=BUCKETS.get("images", "forestguard-images"),
                )
                db.delete(asset)
                hd_deleted += 1
            except Exception as e:
                logger.warning(
                    "cleanup_asset_delete_failed asset_id=%s error=%s", asset.id, e
                )
                hd_errors += 1

        db.commit()

        logger.info(
            "cleanup_completed hd_deleted=%d hd_errors=%d "
            "hd_cutoff_days=%d pdf_cutoff_days=%d",
            hd_deleted,
            hd_errors,
            hd_retention_days,
            pdf_retention_days,
        )

        return {
            "hd_deleted": hd_deleted,
            "hd_errors": hd_errors,
            "hd_cutoff_date": hd_cutoff.isoformat(),
            "pdf_retention_days": pdf_retention_days,
        }

    except Exception as e:
        logger.error("cleanup_failed error=%s", e, exc_info=True)
        raise
    finally:
        db.close()
