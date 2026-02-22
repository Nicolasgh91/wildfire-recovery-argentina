from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api import deps
from app.core.security import require_admin
from app.schemas.imagery import RefreshResponse
from app.services.gee_service import GEEAuthenticationError, GEERateLimitError
from app.services.imagery_service import ImageryService

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(require_admin)])


@router.post(
    "/refresh/{fire_id}",
    response_model=RefreshResponse,
    summary="Force carousel thumbnail refresh (UC-F08)",
    description="Genera nuevos thumbnails del carrusel para un episodio específico.",
)
def refresh_carousel(
    fire_id: UUID,
    db: Session = Depends(deps.get_db),
) -> RefreshResponse:
    service = ImageryService(db)
    try:
        result = service.refresh_fire(str(fire_id), force_refresh=True)
        result.setdefault("fire_id", str(fire_id))
    except GEEAuthenticationError as exc:
        logger.exception("GEE auth failed during manual refresh")
        raise HTTPException(
            status_code=503, detail=f"GEE auth failed: {exc}"
        ) from exc
    except GEERateLimitError as exc:
        logger.exception("GEE rate limit during manual refresh")
        raise HTTPException(
            status_code=503, detail=f"GEE rate limit: {exc}"
        ) from exc

    if result.get("status") == "not_found":
        raise HTTPException(status_code=404, detail="Episode not found")

    return RefreshResponse(**result)
