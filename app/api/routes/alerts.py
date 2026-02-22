import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.alerts import ParkAlert
from app.models.region import ProtectedArea
from app.schemas.alerts import (
    ParkCapacityAlertRequest,
    ParkCapacityAlertResponse,
)
from app.services.alerts_service import assess_park_capacity

router = APIRouter()


@router.post(
    "/park-capacity",
    response_model=ParkCapacityAlertResponse,
    summary="Park carrying capacity alert (UC-04)",
    description="Generates an alert based on visitor load and climate risk.",
)
def create_park_capacity_alert(
    request: ParkCapacityAlertRequest, db: Session = Depends(get_db)
) -> ParkCapacityAlertResponse:
    """Create a park carrying-capacity alert using visitor load and climate risk."""
    protected_area = (
        db.query(ProtectedArea)
        .filter(ProtectedArea.id == request.protected_area_id)
        .first()
    )

    if not protected_area:
        raise HTTPException(status_code=404, detail="Protected area not found")

    carrying_capacity = (
        request.carrying_capacity or protected_area.carrying_capacity
    )
    if not carrying_capacity:
        raise HTTPException(
            status_code=400,
            detail="Carrying capacity not defined for protected area",
        )

    assessment = assess_park_capacity(
        visitor_count=request.visitor_count,
        carrying_capacity=carrying_capacity,
        climate=request.climate,
    )

    alert = ParkAlert(
        protected_area_id=request.protected_area_id,
        alert_date=request.alert_date,
        visitor_count=request.visitor_count,
        carrying_capacity=carrying_capacity,
        occupancy_pct=assessment.occupancy_pct,
        risk_score=assessment.risk_score,
        risk_level=assessment.risk_level,
        alert_level=assessment.alert_level,
        climate_summary=json.dumps(request.climate.model_dump())
        if request.climate
        else None,
        recommended_action=assessment.recommended_action,
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)

    return ParkCapacityAlertResponse(
        alert_id=alert.id,
        protected_area_id=request.protected_area_id,
        alert_date=request.alert_date,
        visitor_count=request.visitor_count,
        carrying_capacity=carrying_capacity,
        occupancy_pct=assessment.occupancy_pct,
        risk_score=assessment.risk_score,
        risk_level=assessment.risk_level,
        alert_level=assessment.alert_level,
        recommended_action=assessment.recommended_action,
        created_at=alert.created_at or datetime.utcnow(),
    )
