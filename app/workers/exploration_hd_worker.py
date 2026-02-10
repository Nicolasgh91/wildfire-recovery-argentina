from __future__ import annotations

import hashlib
import json
import logging
import time
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.exploration import (
    HdGenerationJob,
    InvestigationAsset,
    InvestigationItem,
    UserInvestigation,
)
from app.models.fire import FireEvent
from app.services.fire_service import CENTROID_GEOMETRY, PERIMETER_GEOMETRY
from app.services.gee_service import GEEError, GEEImageNotFoundError, GEEService
from app.services.storage_service import BUCKETS, StorageService

logger = logging.getLogger(__name__)

DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF_SECONDS = 2
DEFAULT_BBOX_BUFFER_DEGREES = 0.01  # ~1km


def _log_metric(name: str, value: float, **labels: Any) -> None:
    payload = {"metric": name, "value": value, "labels": labels}
    logger.info("metric=%s", json.dumps(payload, ensure_ascii=True))


def _normalize_bbox(aoi: Optional[Dict[str, Any]]) -> Optional[Dict[str, float]]:
    if not isinstance(aoi, dict):
        return None

    required = {"west", "south", "east", "north"}
    if not required.issubset(aoi.keys()):
        return None

    try:
        return {
            "west": float(aoi["west"]),
            "south": float(aoi["south"]),
            "east": float(aoi["east"]),
            "north": float(aoi["north"]),
        }
    except (TypeError, ValueError):
        return None


def _fallback_bbox(
    lat: Optional[float], lon: Optional[float]
) -> Optional[Dict[str, float]]:
    if lat is None or lon is None:
        return None
    return {
        "west": lon - DEFAULT_BBOX_BUFFER_DEGREES,
        "south": lat - DEFAULT_BBOX_BUFFER_DEGREES,
        "east": lon + DEFAULT_BBOX_BUFFER_DEGREES,
        "north": lat + DEFAULT_BBOX_BUFFER_DEGREES,
    }


def _fetch_item_context(db: Session, item_id: UUID):
    perimeter = func.cast(FireEvent.perimeter, PERIMETER_GEOMETRY)
    row = (
        db.query(
            InvestigationItem,
            UserInvestigation,
            FireEvent,
            func.ST_XMin(perimeter).label("bbox_minx"),
            func.ST_YMin(perimeter).label("bbox_miny"),
            func.ST_XMax(perimeter).label("bbox_maxx"),
            func.ST_YMax(perimeter).label("bbox_maxy"),
            func.ST_X(func.cast(FireEvent.centroid, CENTROID_GEOMETRY)).label("lon"),
            func.ST_Y(func.cast(FireEvent.centroid, CENTROID_GEOMETRY)).label("lat"),
        )
        .join(
            UserInvestigation,
            UserInvestigation.id == InvestigationItem.investigation_id,
        )
        .join(FireEvent, FireEvent.id == UserInvestigation.fire_event_id)
        .filter(InvestigationItem.id == item_id)
        .first()
    )
    return row


def generate_hd_image_for_item(
    item_id: UUID,
    *,
    max_retries: int = DEFAULT_MAX_RETRIES,
    backoff_seconds: int = DEFAULT_BACKOFF_SECONDS,
) -> bool:
    start_time = time.monotonic()
    db = SessionLocal()
    try:
        row = _fetch_item_context(db, item_id)
        if not row:
            logger.error("exploration_item_not_found item_id=%s", item_id)
            return False

        (
            item,
            investigation,
            fire_event,
            bbox_minx,
            bbox_miny,
            bbox_maxx,
            bbox_maxy,
            lon,
            lat,
        ) = row

        if item.status == "generated":
            logger.info("exploration_item_already_generated item_id=%s", item_id)
            return True

        bbox = _normalize_bbox(item.aoi)
        if not bbox and None not in (bbox_minx, bbox_miny, bbox_maxx, bbox_maxy):
            bbox = {
                "west": float(bbox_minx),
                "south": float(bbox_miny),
                "east": float(bbox_maxx),
                "north": float(bbox_maxy),
            }
        if not bbox:
            bbox = _fallback_bbox(lat, lon)

        if not bbox:
            item.status = "failed"
            item.error = "Missing AOI/bbox information"
            item.updated_at = datetime.now(timezone.utc)
            db.commit()
            return False

        vis_params = item.visualization_params or {}
        vis_type = str(vis_params.get("vis_type", "RGB"))
        max_cloud_cover = float(vis_params.get("max_cloud_cover", 40))
        dimensions = int(vis_params.get("dimensions", 1920))
        image_format = str(vis_params.get("format", "png")).lower()

        target_date = item.target_date.date()
        window_days = int(vis_params.get("window_days", 15))
        start_date = target_date - timedelta(days=window_days)
        end_date = target_date + timedelta(days=window_days)

        gee = GEEService()
        gee.authenticate()
        requests_before = gee.get_request_count()

        last_error: Optional[str] = None
        image_bytes: Optional[bytes] = None
        metadata = None

        for attempt in range(1, max_retries + 1):
            try:
                collection = gee.get_sentinel_collection(
                    bbox=bbox,
                    start_date=start_date,
                    end_date=end_date,
                    max_cloud_cover=max_cloud_cover,
                )
                image = gee.get_best_image(collection, target_date=target_date)
                metadata = gee.get_image_metadata(image)
                image_bytes = gee.download_thumbnail(
                    image=image,
                    bbox=bbox,
                    vis_type=vis_type,
                    dimensions=dimensions,
                    format=image_format,
                )
                last_error = None
                break
            except (GEEImageNotFoundError, GEEError, ValueError) as exc:
                last_error = str(exc)
                logger.warning(
                    "gee_request_failed item_id=%s attempt=%s error=%s",
                    item_id,
                    attempt,
                    last_error,
                )
            except Exception as exc:  # pragma: no cover - defensive
                last_error = str(exc)
                logger.exception(
                    "unexpected_gee_error item_id=%s attempt=%s", item_id, attempt
                )

            time.sleep(backoff_seconds * attempt)

        if image_bytes is None:
            item.status = "failed"
            item.error = last_error or "Unable to generate image"
            item.updated_at = datetime.now(timezone.utc)
            db.commit()
            _log_metric(
                "gee_requests_failed_total",
                1,
                item_id=str(item_id),
                sensor=item.sensor or "sentinel-2",
                target_date=target_date.isoformat(),
            )
            return False

        storage = StorageService()
        key = f"explorations/{investigation.id}/{item.id}.{image_format}"
        content_type = f"image/{image_format}"
        upload = storage.upload_bytes(
            data=image_bytes,
            key=key,
            bucket=BUCKETS["images"],
            content_type=content_type,
            metadata={
                "investigation_id": str(investigation.id),
                "item_id": str(item.id),
            },
        )

        if not upload.success:
            item.status = "failed"
            item.error = upload.error or "Upload failed"
            item.updated_at = datetime.now(timezone.utc)
            db.commit()
            return False

        asset = (
            db.query(InvestigationAsset)
            .filter(InvestigationAsset.investigation_item_id == item.id)
            .first()
        )
        if not asset:
            asset = InvestigationAsset(investigation_item_id=item.id)
            db.add(asset)

        sha256 = upload.content_hash or hashlib.sha256(image_bytes).hexdigest()
        asset.gcs_path = upload.key
        asset.signed_url_cache = None
        asset.mime = content_type
        asset.width = dimensions if dimensions else None
        asset.height = None
        asset.sha256 = sha256
        asset.generated_at = datetime.now(timezone.utc)
        asset.recipe = {
            "bbox": bbox,
            "target_date": target_date.isoformat(),
            "window_start": start_date.isoformat(),
            "window_end": end_date.isoformat(),
            "sensor": item.sensor or "sentinel-2",
            "vis_type": vis_type,
            "visualization_params": vis_params,
            "gee_image_id": metadata.image_id if metadata else None,
            "cloud_cover": metadata.cloud_cover_percent if metadata else None,
        }

        item.status = "generated"
        item.error = None
        item.updated_at = datetime.now(timezone.utc)
        db.commit()

        requests_after = gee.get_request_count()
        requests_delta = max(requests_after - requests_before, 0)

        duration = time.monotonic() - start_time
        _log_metric("images_generated_total", 1, item_id=str(item_id))
        _log_metric("hd_generation_time_seconds", duration, item_id=str(item_id))
        _log_metric(
            "gee_requests_total",
            requests_delta,
            item_id=str(item_id),
            sensor=item.sensor or "sentinel-2",
            target_date=target_date.isoformat(),
        )
        return True
    finally:
        db.close()


def _update_job_progress(job_id: UUID, progress_done: int) -> None:
    db = SessionLocal()
    try:
        with db.begin():
            job = (
                db.query(HdGenerationJob)
                .filter(HdGenerationJob.id == job_id)
                .with_for_update()
                .first()
            )
            if not job:
                return
            job.progress_done = min(progress_done, job.progress_total or progress_done)
    finally:
        db.close()


def run_generation_job(job_id: UUID) -> None:
    db = SessionLocal()
    try:
        with db.begin():
            job = (
                db.query(HdGenerationJob)
                .filter(HdGenerationJob.id == job_id)
                .with_for_update()
                .first()
            )
            if not job:
                logger.error("generation_job_not_found job_id=%s", job_id)
                return
            if job.status in ("ready", "failed"):
                logger.info("generation_job_already_finished job_id=%s", job_id)
                return

            investigation = (
                db.query(UserInvestigation)
                .filter(UserInvestigation.id == job.investigation_id)
                .first()
            )
            if not investigation:
                job.status = "failed"
                job.finished_at = datetime.now(timezone.utc)
                return

            items_count = (
                db.query(func.count(InvestigationItem.id))
                .filter(InvestigationItem.investigation_id == investigation.id)
                .scalar()
                or 0
            )
            job.progress_total = items_count
            if job.status == "queued":
                job.status = "processing"
                job.started_at = datetime.now(timezone.utc)

    finally:
        db.close()

    db = SessionLocal()
    try:
        item_ids = [
            row[0]
            for row in (
                db.query(InvestigationItem.id)
                .filter(InvestigationItem.investigation_id == job.investigation_id)
                .order_by(InvestigationItem.target_date.asc())
                .all()
            )
        ]
    finally:
        db.close()

    progress_done = 0
    for item_id in item_ids:
        generate_hd_image_for_item(item_id)
        progress_done += 1
        _update_job_progress(job_id, progress_done)

    db = SessionLocal()
    try:
        with db.begin():
            job = (
                db.query(HdGenerationJob)
                .filter(HdGenerationJob.id == job_id)
                .with_for_update()
                .first()
            )
            if not job:
                return

            failed_items = (
                db.query(func.count(InvestigationItem.id))
                .filter(
                    InvestigationItem.investigation_id == job.investigation_id,
                    InvestigationItem.status == "failed",
                )
                .scalar()
                or 0
            )

            job.status = "failed" if failed_items > 0 else "ready"
            job.finished_at = datetime.now(timezone.utc)

            investigation = (
                db.query(UserInvestigation)
                .filter(UserInvestigation.id == job.investigation_id)
                .first()
            )
            if investigation:
                investigation.status = job.status
                investigation.updated_at = datetime.now(timezone.utc)

            if failed_items:
                _log_metric(
                    "gee_requests_failed_total", failed_items, job_id=str(job_id)
                )
    finally:
        db.close()
