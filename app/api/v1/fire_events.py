from __future__ import annotations

from datetime import date
from typing import List, Optional, Tuple
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api import deps
from app.core.rate_limiter import check_rate_limit
from app.schemas.fire import ExplorationPreviewResponse, FireSearchResponse
from app.services.fire_service import FireFilterParams, FireService

router = APIRouter()


def get_fire_service(db: Session = Depends(deps.get_db)) -> FireService:
    return FireService(db)


def _parse_bbox(
    bbox: Optional[str],
) -> Optional[Tuple[float, float, float, float]]:
    if not bbox:
        return None

    parts = [p.strip() for p in bbox.split(",") if p.strip()]
    if len(parts) != 4:
        raise HTTPException(
            status_code=400,
            detail="bbox must be 'west,south,east,north' with 4 comma-separated values",
        )

    try:
        west, south, east, north = [float(p) for p in parts]
    except ValueError as exc:
        raise HTTPException(
            status_code=400, detail="bbox values must be numeric"
        ) from exc

    if west >= east or south >= north:
        raise HTTPException(status_code=400, detail="bbox bounds are invalid")

    if not (-180 <= west <= 180 and -180 <= east <= 180):
        raise HTTPException(
            status_code=400, detail="bbox longitude out of range"
        )
    if not (-90 <= south <= 90 and -90 <= north <= 90):
        raise HTTPException(
            status_code=400, detail="bbox latitude out of range"
        )

    return west, south, east, north


@router.get(
    "/search",
    response_model=FireSearchResponse,
    summary="Buscar incendios (exploraciÃ³n)",
    description="BÃºsqueda humana por provincia, fechas, texto libre y bbox.",
    dependencies=[Depends(check_rate_limit)],
)
def search_fire_events(
    province: Optional[List[str]] = Query(None, description="Provincia(s)"),
    date_from: Optional[date] = Query(None, description="Fecha desde"),
    date_to: Optional[date] = Query(None, description="Fecha hasta"),
    q: Optional[str] = Query(None, max_length=100, description="Texto libre"),
    bbox: Optional[str] = Query(None, description="west,south,east,north"),
    page: int = Query(1, ge=1, description="PÃ¡gina"),
    page_size: Optional[int] = Query(
        None, ge=1, description="Items por pÃ¡gina"
    ),
    service: FireService = Depends(get_fire_service),
) -> FireSearchResponse:
    search_value = q.strip() if q and len(q.strip()) >= 2 else None
    bbox_values = _parse_bbox(bbox)

    params = FireFilterParams(
        province=province,
        date_from=date_from,
        date_to=date_to,
        search=search_value,
        bbox=bbox_values,
    )

    return service.search_fire_events(
        params=params,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{fire_event_id}/exploration-preview",
    response_model=ExplorationPreviewResponse,
    summary="Preview de exploraciÃ³n sin GEE",
    description="Devuelve perÃ­metro, bbox, fechas clave y timeline sugerida.",
    dependencies=[Depends(check_rate_limit)],
)
def get_exploration_preview(
    fire_event_id: UUID,
    service: FireService = Depends(get_fire_service),
) -> ExplorationPreviewResponse:
    result = service.get_exploration_preview(fire_event_id)
    if not result:
        raise HTTPException(status_code=404, detail="Evento no encontrado")
    return result
