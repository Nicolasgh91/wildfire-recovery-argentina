from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api import deps
from app.core.security import verify_api_key
from app.schemas.analysis import RecurrenceResponse, TrendsResponse
from app.services.recurrence_service import BBox, RecurrenceService
from app.services.trends_service import TrendsService

router = APIRouter()


def get_recurrence_service(
    db: Session = Depends(deps.get_db),
) -> RecurrenceService:
    return RecurrenceService(db)


def get_trends_service(db: Session = Depends(deps.get_db)) -> TrendsService:
    return TrendsService(db)


@router.get(
    "/recurrence",
    response_model=RecurrenceResponse,
    summary="H3 recurrence heatmap (UC-F05)",
    dependencies=[Depends(verify_api_key)],
)
def get_recurrence(
    min_lon: float = Query(..., ge=-180, le=180),
    min_lat: float = Query(..., ge=-90, le=90),
    max_lon: float = Query(..., ge=-180, le=180),
    max_lat: float = Query(..., ge=-90, le=90),
    service: RecurrenceService = Depends(get_recurrence_service),
) -> RecurrenceResponse:
    if min_lon >= max_lon or min_lat >= max_lat:
        raise HTTPException(status_code=400, detail="Invalid bbox")

    bbox = BBox(
        min_lon=min_lon, min_lat=min_lat, max_lon=max_lon, max_lat=max_lat
    )
    try:
        return service.get_recurrence(bbox)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get(
    "/trends",
    response_model=TrendsResponse,
    summary="Fire trends and forecasting (UC-F05)",
    dependencies=[Depends(verify_api_key)],
)
def get_trends(
    date_from: date = Query(..., description="Start date"),
    date_to: date = Query(..., description="End date"),
    min_lon: Optional[float] = Query(None, ge=-180, le=180),
    min_lat: Optional[float] = Query(None, ge=-90, le=90),
    max_lon: Optional[float] = Query(None, ge=-180, le=180),
    max_lat: Optional[float] = Query(None, ge=-90, le=90),
    service: TrendsService = Depends(get_trends_service),
) -> TrendsResponse:
    bbox = None
    if None not in (min_lon, min_lat, max_lon, max_lat):
        if min_lon >= max_lon or min_lat >= max_lat:
            raise HTTPException(status_code=400, detail="Invalid bbox")
        bbox = {
            "min_lon": min_lon,
            "min_lat": min_lat,
            "max_lon": max_lon,
            "max_lat": max_lat,
        }

    try:
        return service.get_trends(
            date_from=date_from, date_to=date_to, bbox=bbox
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
