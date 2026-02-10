from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api import deps
from app.core.security import verify_api_key
from app.schemas.quality import QualityResponse
from app.services.quality_service import QualityService

router = APIRouter()


def get_quality_service(db: Session = Depends(deps.get_db)) -> QualityService:
    return QualityService(db)


@router.get(
    "/fire-event/{fire_event_id}",
    response_model=QualityResponse,
    summary="Quality and reliability metrics (UC-F04)",
    dependencies=[Depends(verify_api_key)],
)
def get_quality(
    fire_event_id: UUID,
    service: QualityService = Depends(get_quality_service),
) -> QualityResponse:
    result = service.get_quality(fire_event_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evento no encontrado",
        )
    return result
