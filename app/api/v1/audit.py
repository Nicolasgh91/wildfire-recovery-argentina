"""
=============================================================================
FORESTGUARD API - LAND USE AUDIT ENDPOINTS (UC-01)
=============================================================================

Legal land-use verification under Argentina's Forest Law (Ley 26.815 Art. 22 bis).

Use Case (UC-01): Auditoría de Uso de Suelo
    Verifies if a parcel of land has legal restrictions due to previous
    wildfire events. Restrictions apply for 60 years post-fire when land
    was in a protected area or suffered significant damage.

Endpoints:
    POST /audit/land-use - Check legal restrictions for coordinates
    GET /audit/geocode - Geocode an address to coordinates

Authentication:
    All endpoints require API key authentication.

Legal Framework:
    - Ley 26.815 Art. 22 bis (Argentina)
    - 60-year restriction period for affected lands
    - Applies to land-use change, construction permits, subdivisions

Author: ForestGuard Team
Version: 2.0.0
Last Updated: 2026-02-08
=============================================================================
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.api import deps
from app.core.rate_limiter import check_rate_limit
from app.core.security import verify_api_key
from app.schemas.audit import AuditRequest, AuditResponse
from app.schemas.geocode import GeocodeResponse
from app.services.audit_service import AuditService
from app.services.geocoding_service import GeocodingService

router = APIRouter()


def get_audit_service(db: Session = Depends(deps.get_db)) -> AuditService:
    return AuditService(db)


def get_geocoding_service() -> GeocodingService:
    return GeocodingService()


@router.post(
    "/land-use",
    response_model=AuditResponse,
    summary="Legal land-use audit (UC-F06)",
    dependencies=[Depends(verify_api_key), Depends(check_rate_limit)],
)
def audit_land_use(
    payload: AuditRequest,
    request: Request,
    service: AuditService = Depends(get_audit_service),
) -> AuditResponse:
    try:
        user_ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
        return service.run_audit(
            lat=payload.lat,
            lon=payload.lon,
            radius_meters=payload.radius_meters,
            cadastral_id=payload.cadastral_id,
            user_ip=user_ip,
            user_agent=user_agent,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get(
    "/geocode",
    response_model=GeocodeResponse,
    summary="Geocodificar una ubicaciÃ³n (audit)",
    dependencies=[Depends(verify_api_key), Depends(check_rate_limit)],
)
def geocode_location(
    q: str = Query(
        ..., min_length=3, max_length=120, description="Texto a geocodificar"
    ),
    service: GeocodingService = Depends(get_geocoding_service),
) -> GeocodeResponse:
    result = service.geocode(q.strip())
    if not result:
        raise HTTPException(
            status_code=404, detail="No se encontraron resultados"
        )
    return GeocodeResponse(query=q, result=result)
