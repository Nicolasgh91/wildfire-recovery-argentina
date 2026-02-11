from __future__ import annotations

import csv
import io
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

from fastapi import HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.fire import FireEvent
from app.schemas.fire import ExportFormat, ExportRequestStatus, FireStatus

logger = logging.getLogger(__name__)

EXPORT_SYNC_LIMIT = 1000
EXPORT_MAX_RECORDS = 10000


class ExportService:
    """Service for exporting fire event datasets."""
    def __init__(self, db: Session):
        self.db = db

    def _resolve_fire_status(self, fire: FireEvent) -> FireStatus:
        if fire.status:
            try:
                return FireStatus(fire.status)
            except ValueError:
                pass

        now = datetime.now(timezone.utc)
        if fire.end_date:
            end_date = fire.end_date
            if end_date.tzinfo is None:
                end_date = end_date.replace(tzinfo=timezone.utc)
            days_since_end = (now - end_date).days
            if days_since_end < 0:
                return FireStatus.ACTIVE
            if days_since_end < 3:
                return FireStatus.CONTROLLED
            if days_since_end < 14:
                return FireStatus.MONITORING
        return FireStatus.EXTINGUISHED

    def _count_records(self, query) -> int:
        return (
            query.order_by(None).with_entities(func.count(FireEvent.id)).scalar() or 0
        )

    def export_fires(
        self,
        *,
        query,
        export_format: ExportFormat,
        filters_applied: Dict[str, Any],
        max_records: Optional[int] = None,
        sync_limit: int = EXPORT_SYNC_LIMIT,
    ):
        hard_cap = EXPORT_MAX_RECORDS
        if max_records is None:
            max_records = hard_cap
        max_records = min(max_records, hard_cap)

        total_records = self._count_records(query)
        export_limit = min(total_records, max_records)

        if settings.ENVIRONMENT == "production" and total_records > max_records:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Export exceeds maximum allowed records.",
            )
        if total_records > max_records:
            logger.warning(
                "Export capped to %s records (total=%s)", max_records, total_records
            )

        if settings.ENVIRONMENT == "production" and total_records > sync_limit:
            job_id = str(uuid4())
            logger.info("Export scheduled job_id=%s records=%s", job_id, total_records)
            return ExportRequestStatus(
                status="accepted",
                message="Export scheduled for background processing.",
                job_id=job_id,
                total_records=total_records,
            )

        rows = query.limit(export_limit).all()
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

        if export_format == ExportFormat.CSV:
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(
                [
                    "id",
                    "start_date",
                    "end_date",
                    "duration_hours",
                    "latitude",
                    "longitude",
                    "province",
                    "department",
                    "total_detections",
                    "avg_confidence",
                    "max_frp",
                    "estimated_area_hectares",
                    "is_significant",
                    "has_satellite_imagery",
                    "protected_area_name",
                    "in_protected_area",
                    "overlap_percentage",
                    "count_protected_areas",
                    "status",
                ]
            )

            for row in rows:
                (
                    fire,
                    lat,
                    lon,
                    has_imagery,
                    pa_name,
                    pa_id,
                    overlap_percentage,
                    protected_area_count,
                ) = row
                duration_hours = (
                    (fire.end_date - fire.start_date).total_seconds() / 3600
                    if fire.end_date and fire.start_date
                    else 0
                )
                writer.writerow(
                    [
                        str(fire.id),
                        fire.start_date.isoformat() if fire.start_date else None,
                        fire.end_date.isoformat() if fire.end_date else None,
                        duration_hours,
                        lat,
                        lon,
                        fire.province,
                        fire.department,
                        fire.total_detections,
                        float(fire.avg_confidence) if fire.avg_confidence else 0,
                        float(fire.max_frp) if fire.max_frp else 0,
                        float(fire.estimated_area_hectares)
                        if fire.estimated_area_hectares
                        else 0,
                        bool(fire.is_significant),
                        bool(has_imagery),
                        pa_name,
                        pa_id is not None,
                        float(overlap_percentage)
                        if overlap_percentage is not None
                        else None,
                        int(protected_area_count) if protected_area_count else 0,
                        self._resolve_fire_status(fire).value,
                    ]
                )

            output.seek(0)
            return StreamingResponse(
                iter([output.getvalue()]),
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename=fires_{timestamp}.csv"
                },
            )

        data = {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "total_records": len(rows),
            "filters_applied": filters_applied,
            "fires": [],
        }

        for row in rows:
            (
                fire,
                lat,
                lon,
                has_imagery,
                pa_name,
                pa_id,
                overlap_percentage,
                protected_area_count,
            ) = row
            duration_hours = (
                (fire.end_date - fire.start_date).total_seconds() / 3600
                if fire.end_date and fire.start_date
                else 0
            )
            data["fires"].append(
                {
                    "id": str(fire.id),
                    "start_date": fire.start_date.isoformat()
                    if fire.start_date
                    else None,
                    "end_date": fire.end_date.isoformat() if fire.end_date else None,
                    "duration_hours": duration_hours,
                    "latitude": lat,
                    "longitude": lon,
                    "province": fire.province,
                    "department": fire.department,
                    "total_detections": fire.total_detections,
                    "avg_confidence": float(fire.avg_confidence)
                    if fire.avg_confidence
                    else 0,
                    "max_frp": float(fire.max_frp) if fire.max_frp else 0,
                    "estimated_area_hectares": float(fire.estimated_area_hectares)
                    if fire.estimated_area_hectares
                    else 0,
                    "is_significant": bool(fire.is_significant),
                    "has_satellite_imagery": bool(has_imagery),
                    "protected_area_name": pa_name,
                    "in_protected_area": pa_id is not None,
                    "overlap_percentage": float(overlap_percentage)
                    if overlap_percentage is not None
                    else None,
                    "count_protected_areas": int(protected_area_count)
                    if protected_area_count
                    else 0,
                    "status": self._resolve_fire_status(fire).value,
                }
            )

        filename = f"fires_{timestamp}.json"
        return StreamingResponse(
            iter([json.dumps(data, indent=2, ensure_ascii=False)]),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
