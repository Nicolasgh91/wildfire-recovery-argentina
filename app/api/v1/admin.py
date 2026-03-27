"""Admin endpoints for system monitoring."""
from __future__ import annotations

import csv
import logging
import re
import time
from pathlib import Path
from threading import Lock
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.api import deps
from app.api.auth_deps import get_current_user
from app.core.gee_semaphore import gee_semaphore
from app.models.episode import FireEpisode
from app.models.exploration import InvestigationAsset
from app.models.user import User
from workers.celery_app import celery_app
from workers.tasks.ingestion import run_full_ingestion_pipeline

logger = logging.getLogger(__name__)

router = APIRouter()
UPLOAD_DIR = Path("/tmp/firms_uploads")
DEFAULT_MAX_UPLOAD_MB = 50
MANUAL_INGEST_RATE_WINDOW_SECONDS = 10 * 60
_manual_ingest_last_by_user: dict[str, float] = {}
_manual_ingest_lock = Lock()

REQUIRED_FIRMS_HEADERS = {
    "latitude",
    "longitude",
    "brightness",
    "scan",
    "track",
    "acq_date",
    "acq_time",
    "satellite",
    "instrument",
    "confidence",
    "version",
    "bright_t31",
    "frp",
    "daynight",
    "type",
}


def _sanitize_filename(name: str) -> str:
    candidate = Path(name or "upload.csv").name
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", candidate)
    return safe or "upload.csv"


def _resolve_manual_ingest_max_mb(db: Session) -> int:
    try:
        row = (
            db.execute(
                text(
                    """
                    SELECT param_value
                    FROM system_parameters
                    WHERE param_key = 'manual_ingest_max_upload_mb'
                    LIMIT 1
                    """
                )
            )
            .mappings()
            .first()
        )
        if not row:
            return DEFAULT_MAX_UPLOAD_MB
        value = row.get("param_value")
        if isinstance(value, dict):
            value = value.get("value")
        parsed = int(value)
        return parsed if parsed > 0 else DEFAULT_MAX_UPLOAD_MB
    except Exception:
        return DEFAULT_MAX_UPLOAD_MB


def _validate_csv_headers(csv_path: Path) -> list[str]:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = {str(h).strip() for h in (reader.fieldnames or []) if h}
    missing = sorted(REQUIRED_FIRMS_HEADERS.difference(headers))
    return missing


def _enforce_manual_ingest_rate_limit(user_id: str) -> None:
    now = time.time()
    with _manual_ingest_lock:
        last = _manual_ingest_last_by_user.get(user_id)
        if last and (now - last) < MANUAL_INGEST_RATE_WINDOW_SECONDS:
            retry_after = int(MANUAL_INGEST_RATE_WINDOW_SECONDS - (now - last))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "detail": "Solo se permite una ingesta manual cada 10 minutos por admin.",
                    "retry_after": retry_after,
                },
            )
        _manual_ingest_last_by_user[user_id] = now


@router.get("/storage-usage", tags=["admin"])
def get_storage_usage(db: Session = Depends(deps.get_db)):
    """
    Return storage and GEE usage metrics.
    For administrators only.
    """
    # GEE semaphore usage
    gee_usage = gee_semaphore.get_usage()

    # Count HD assets in DB
    total_assets = db.query(func.count(InvestigationAsset.id)).scalar() or 0

    # Count episodes with valid slides
    episodes_with_slides = (
        db.execute(
            text(
                "SELECT COUNT(*) FROM fire_episodes "
                "WHERE slides_data IS NOT NULL "
                "AND jsonb_array_length(slides_data) > 0"
            )
        ).scalar()
        or 0
    )

    total_episodes = db.query(func.count(FireEpisode.id)).scalar() or 0

    slides_pct = (
        round(episodes_with_slides / total_episodes * 100, 1)
        if total_episodes > 0
        else 0
    )

    return {
        "gee": gee_usage,
        "storage": {
            "total_hd_assets": total_assets,
            "episodes_with_slides": episodes_with_slides,
            "episodes_total": total_episodes,
            "slides_coverage_pct": slides_pct,
        },
        "note": "Para uso real de storage en bytes, consultar la consola de Oracle Cloud.",
    }


@router.post(
    "/ingest-firms",
    status_code=status.HTTP_202_ACCEPTED,
    tags=["admin"],
)
async def upload_firms_csv(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(deps.get_db),
):
    """Upload FIRMS CSV and enqueue full ingestion pipeline."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required.",
        )

    _enforce_manual_ingest_rate_limit(str(current_user.id))

    filename = file.filename or ""
    if not filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El archivo debe tener extensión .csv",
        )

    allowed_types = {"text/csv", "application/octet-stream", "application/vnd.ms-excel"}
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Content-Type no permitido: {file.content_type}",
        )

    max_mb = _resolve_manual_ingest_max_mb(db)
    max_bytes = max_mb * 1024 * 1024
    content = await file.read()
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Archivo excede tamaño máximo de {max_mb} MB",
        )

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = _sanitize_filename(filename)
    target_path = UPLOAD_DIR / f"{uuid4().hex}_{safe_name}"
    target_path.write_bytes(content)

    missing_headers = _validate_csv_headers(target_path)
    if missing_headers:
        target_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "detail": "CSV inválido: faltan columnas requeridas.",
                "missing_headers": missing_headers,
            },
        )

    task = run_full_ingestion_pipeline.delay(str(target_path), source_label="admin_upload")
    return {"task_id": task.id, "status": "queued"}


@router.get("/ingest-firms/{task_id}", tags=["admin"])
async def get_ingestion_status(
    task_id: str,
    current_user: User = Depends(get_current_user),
):
    """Get manual ingestion task status by task_id."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required.",
        )

    task = celery_app.AsyncResult(task_id)
    return {
        "task_id": task_id,
        "status": task.status,
        "result": task.result if task.ready() else None,
        "error": str(task.info) if task.failed() else None,
    }
