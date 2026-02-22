"""
Worker-triggered endpoints for background processing.

UC-08: Post-fire land use change detection.
"""

import logging
from datetime import date, datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.citizen import LandUseChange
from app.services.vae_service import VAEService

logger = logging.getLogger(__name__)

router = APIRouter()


class LandUseChangeRequest(BaseModel):
    fire_event_id: UUID = Field(..., description="Fire event UUID")
    analysis_date: Optional[date] = Field(
        None, description="Optional analysis date"
    )
    buffer_degrees: float = Field(
        default=0.01,
        ge=0.001,
        le=0.1,
        description="BBox buffer around centroid in degrees (~0.01 ≈ 1km)",
    )


class LandUseChangeResponse(BaseModel):
    fire_event_id: UUID
    analysis_date: date
    months_after_fire: int
    change_detected: bool
    change_type: str
    confidence: float
    affected_area_hectares: float
    centroid: dict
    is_potential_violation: bool
    violation_severity: str
    ndvi_before: float
    ndvi_after: float
    ndvi_change: float
    geometric_index: float
    texture_change: float
    requires_field_verification: bool
    recommended_action: str
    record_saved: bool = False


@router.post(
    "/detect-land-use-change",
    response_model=LandUseChangeResponse,
    summary="Detect post-fire land use changes (UC-08)",
    description="""
    Detects post-fire land use changes that may indicate illegal activity.
    Intended to be triggered by workers or scheduled jobs.
    """,
)
def detect_land_use_change(
    request: LandUseChangeRequest, db: Session = Depends(get_db)
) -> LandUseChangeResponse:
    """
    Run VAE land-use change detection for a fire event and optionally persist results.
    """
    fire_query = text(
        """
        SELECT
            id,
            start_date,
            estimated_area_hectares,
            ST_Y(centroid::geometry) as lat,
            ST_X(centroid::geometry) as lon
        FROM fire_events
        WHERE id = :fire_id
    """
    )

    result = db.execute(
        fire_query, {"fire_id": str(request.fire_event_id)}
    ).fetchone()
    if not result:
        raise HTTPException(status_code=404, detail="Fire event not found")

    fire_date = (
        result.start_date.date()
        if hasattr(result.start_date, "date")
        else result.start_date
    )
    analysis_date = request.analysis_date or date.today()
    area_hectares = float(result.estimated_area_hectares or 0)

    bbox = {
        "west": result.lon - request.buffer_degrees,
        "south": result.lat - request.buffer_degrees,
        "east": result.lon + request.buffer_degrees,
        "north": result.lat + request.buffer_degrees,
    }

    try:
        vae = VAEService()
        analysis = vae.detect_land_use_change(
            fire_event_id=str(request.fire_event_id),
            bbox=bbox,
            fire_date=fire_date,
            analysis_date=analysis_date,
            area_hectares=area_hectares,
        )
    except Exception as exc:
        logger.exception("Land use change detection failed")
        raise HTTPException(
            status_code=503, detail=f"Detection failed: {exc}"
        ) from exc

    record_saved = False
    try:
        change = LandUseChange(
            fire_event_id=request.fire_event_id,
            change_detected_at=analysis.analysis_date,
            months_after_fire=analysis.months_after_fire,
            change_type=analysis.change_type.value,
            change_severity=analysis.violation_severity.value,
            affected_area_hectares=analysis.affected_area_hectares,
            is_potential_violation=analysis.is_potential_violation,
            violation_confidence=f"{analysis.change_confidence:.2f}",
            status="pending_review",
        )
        db.add(change)
        db.commit()
        record_saved = True
    except Exception:
        db.rollback()
        logger.warning(
            "Unable to persist land use change record", exc_info=True
        )

    return LandUseChangeResponse(
        fire_event_id=request.fire_event_id,
        analysis_date=analysis.analysis_date,
        months_after_fire=analysis.months_after_fire,
        change_detected=analysis.change_detected,
        change_type=analysis.change_type.value,
        confidence=analysis.change_confidence,
        affected_area_hectares=analysis.affected_area_hectares,
        centroid={"lat": analysis.centroid_lat, "lon": analysis.centroid_lon},
        is_potential_violation=analysis.is_potential_violation,
        violation_severity=analysis.violation_severity.value,
        ndvi_before=analysis.before_ndvi,
        ndvi_after=analysis.after_ndvi,
        ndvi_change=analysis.ndvi_change,
        geometric_index=analysis.geometric_index,
        texture_change=analysis.texture_change,
        requires_field_verification=analysis.requires_field_verification,
        recommended_action=analysis.recommended_action,
        record_saved=record_saved,
    )
