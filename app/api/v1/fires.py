"""
=============================================================================
FORESTGUARD API - FIRE EVENTS ENDPOINTS (UC-13, UC-14)
=============================================================================

Core wildfire event management endpoints.

Use Cases:
    - UC-13: Fire Event Listing - Browse and filter detected wildfires
    - UC-14: Fire Event Details - Get comprehensive fire event information

Endpoints:
    GET /fires - List fire events with advanced filtering
    GET /fires/home - Active fires for home page display
    GET /fires/stats - Aggregate statistics and metrics
    GET /fires/export - Export fire data (CSV/GeoJSON)
    GET /fires/{fire_id} - Get detailed fire event information
    GET /filters - List user's saved filters
    POST /filters - Save a filter preset
    DELETE /filters/{filter_id} - Delete a saved filter

Authentication:
    - Public endpoints: list_fires, list_active_fires_for_home, get_fire_detail
    - API Key or JWT required: export_fires, stats
    - JWT required: saved filters management

Rate Limiting:
    All endpoints are rate-limited per IP address.

Author: ForestGuard Team
Version: 2.0.0
Last Updated: 2026-02-08
=============================================================================
"""
from __future__ import annotations

from datetime import date
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Security, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.api import deps
from app.core.security import api_key_header
from app.core.security import get_current_user as verify_api_key_user
from app.models.user import User
from app.schemas.fire import (
    ExportFormat,
    ExportRequestStatus,
    FireDetailResponse,
    FireListResponse,
    SavedFilterCreate,
    SavedFilterListResponse,
    SavedFilterResponse,
    SortField,
    StatsResponse,
    StatusScope,
)
from app.services.supabase_auth import (
    AuthError,
    decode_supabase_token,
    get_or_create_supabase_user,
)
from app.services.export_service import ExportService
from app.services.fire_service import FireFilterParams, FireService

router = APIRouter()
filters_router = APIRouter()
security = HTTPBearer(auto_error=False)


def get_fire_service(db: Session = Depends(deps.get_db)) -> FireService:
    """Return fire service bound to request DB session."""
    return FireService(db)


def get_export_service(db: Session = Depends(deps.get_db)) -> ExportService:
    """Return export service used by fire export endpoints."""
    return ExportService(db)


async def _resolve_jwt_user(
    credentials: HTTPAuthorizationCredentials, db: Session
) -> User:
    """Decode Supabase JWT and resolve/create application user."""
    token = credentials.credentials
    try:
        payload = decode_supabase_token(token)
        return get_or_create_supabase_user(db, payload)
    except AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Token invalido") from exc


async def require_fire_access(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    api_key: Optional[str] = Security(api_key_header),
    db: Session = Depends(deps.get_db),
):
    """Authorize stats/export endpoints using either JWT or API key."""
    if credentials:
        try:
            return await _resolve_jwt_user(credentials, db)
        except HTTPException:
            if api_key:
                await verify_api_key_user(api_key=api_key)
                return None
            raise
    if api_key:
        await verify_api_key_user(api_key=api_key)
        return None
    raise HTTPException(status_code=401, detail="Authentication required")


async def require_jwt_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(deps.get_db),
) -> User:
    """Require and resolve authenticated JWT user for saved-filter operations."""
    if not credentials:
        raise HTTPException(status_code=401, detail="Token requerido")
    return await _resolve_jwt_user(credentials, db)


@router.get(
    "",
    response_model=FireListResponse,
    summary="Listar incendios con filtros (UC-F03)",
    description="Lista eventos de incendio con filtros, paginacion y ordenamiento.",
)
@router.get(
    "/",
    response_model=FireListResponse,
    summary="Listar incendios con filtros (UC-F03)",
    description="Lista eventos de incendio con filtros, paginacion y ordenamiento.",
    include_in_schema=False,
)
def list_fires(
    province: Optional[List[str]] = Query(None, description="Provincia(s)"),
    department: Optional[str] = Query(None, description="Departamento"),
    protected_area_id: Optional[UUID] = Query(
        None, description="ID area protegida"
    ),
    in_protected_area: Optional[bool] = Query(
        None, description="En area protegida"
    ),
    date_from: Optional[date] = Query(None, description="Fecha desde"),
    date_to: Optional[date] = Query(None, description="Fecha hasta"),
    active_only: Optional[bool] = Query(None, description="Solo activos"),
    status_scope: Optional[StatusScope] = Query(
        None, description="active | historical | all"
    ),
    min_confidence: Optional[float] = Query(
        None, description="Confianza minima"
    ),
    min_detections: Optional[int] = Query(
        None, description="Min. detecciones"
    ),
    is_significant: Optional[bool] = Query(
        None, description="Solo significativos"
    ),
    has_imagery: Optional[bool] = Query(None, description="Con imagenes"),
    search: Optional[str] = Query(None, max_length=100, description="Buscar"),
    page: int = Query(1, description="Pagina"),
    page_size: Optional[int] = Query(None, ge=1, le=200, description="Items por pagina (max 200)"),
    sort_by: SortField = Query(
        SortField.START_DATE, description="Ordenar por"
    ),
    sort_desc: bool = Query(True, description="Descendente"),
    service: FireService = Depends(get_fire_service),
) -> FireListResponse:
    search_value = (
        search.strip() if search and len(search.strip()) >= 2 else None
    )

    params = FireFilterParams(
        province=province,
        department=department,
        protected_area_id=protected_area_id,
        in_protected_area=in_protected_area,
        date_from=date_from,
        date_to=date_to,
        active_only=active_only,
        status_scope=status_scope,
        min_confidence=min_confidence,
        min_detections=min_detections,
        is_significant=is_significant,
        has_imagery=has_imagery,
        search=search_value,
    )

    return service.list_fires(
        params=params,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_desc=sort_desc,
    )


@router.get(
    "/active",
    response_model=FireListResponse,
    summary="Incendios para Home con thumbnails",
    description="Retorna incendios activos y extinguidos recientes con thumbnails generados (slides_data).",
)
def list_active_fires_for_home(
    limit: int = Query(
        20, ge=1, le=50, description="Maximo de incendios para Home"
    ),
    service: FireService = Depends(get_fire_service),
) -> FireListResponse:
    return service.list_active_with_thumbnails(limit)


@router.get(
    "/stats",
    response_model=StatsResponse,
    summary="Estadisticas agregadas",
    tags=["stats"],
    dependencies=[Depends(require_fire_access)],
)
def get_statistics(
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    province: Optional[List[str]] = Query(None),
    department: Optional[str] = Query(None),
    protected_area_id: Optional[UUID] = Query(None),
    in_protected_area: Optional[bool] = Query(None),
    active_only: Optional[bool] = Query(None),
    status_scope: Optional[StatusScope] = Query(None),
    min_confidence: Optional[float] = Query(None),
    min_detections: Optional[int] = Query(None),
    is_significant: Optional[bool] = Query(None),
    has_imagery: Optional[bool] = Query(None),
    search: Optional[str] = Query(None, max_length=100),
    service: FireService = Depends(get_fire_service),
) -> StatsResponse:
    search_value = (
        search.strip() if search and len(search.strip()) >= 2 else None
    )

    params = FireFilterParams(
        province=province,
        department=department,
        protected_area_id=protected_area_id,
        in_protected_area=in_protected_area,
        date_from=date_from,
        date_to=date_to,
        active_only=active_only,
        status_scope=status_scope,
        min_confidence=min_confidence,
        min_detections=min_detections,
        is_significant=is_significant,
        has_imagery=has_imagery,
        search=search_value,
    )
    return service.get_stats(params=params)


@router.get(
    "/export",
    summary="Exportar incendios",
    description="Exporta lista de incendios filtrada. Sync <1000, async >1000.",
    dependencies=[Depends(require_fire_access)],
)
def export_fires(
    province: Optional[List[str]] = Query(None),
    department: Optional[str] = Query(None),
    protected_area_id: Optional[UUID] = Query(None),
    in_protected_area: Optional[bool] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    active_only: Optional[bool] = Query(None),
    status_scope: Optional[StatusScope] = Query(None),
    min_confidence: Optional[float] = Query(None),
    min_detections: Optional[int] = Query(None),
    is_significant: Optional[bool] = Query(None),
    has_imagery: Optional[bool] = Query(None),
    search: Optional[str] = Query(None, max_length=100),
    format: ExportFormat = Query(ExportFormat.CSV),
    max_records: Optional[int] = Query(
        default=None,
        ge=1,
        le=10000,
        description="Máximo de registros para exportar (límite: 10000)",
    ),
    service: FireService = Depends(get_fire_service),
    export_service: ExportService = Depends(get_export_service),
):
    search_value = (
        search.strip() if search and len(search.strip()) >= 2 else None
    )

    params = FireFilterParams(
        province=province,
        department=department,
        protected_area_id=protected_area_id,
        in_protected_area=in_protected_area,
        date_from=date_from,
        date_to=date_to,
        active_only=active_only,
        status_scope=status_scope,
        min_confidence=min_confidence,
        min_detections=min_detections,
        is_significant=is_significant,
        has_imagery=has_imagery,
        search=search_value,
    )

    query = service.build_list_query()
    filters = service.build_filter_conditions(params)
    if filters:
        query = query.filter(*filters)

    filters_applied = {
        k: v
        for k, v in {
            "province": province,
            "department": department,
            "protected_area_id": str(protected_area_id)
            if protected_area_id
            else None,
            "in_protected_area": in_protected_area,
            "date_from": date_from.isoformat() if date_from else None,
            "date_to": date_to.isoformat() if date_to else None,
            "active_only": active_only,
            "status_scope": status_scope.value if status_scope else None,
            "min_confidence": min_confidence,
            "min_detections": min_detections,
            "is_significant": is_significant,
            "has_imagery": has_imagery,
            "search": search_value,
        }.items()
        if v is not None
    }

    response = export_service.export_fires(
        query=query,
        export_format=format,
        filters_applied=filters_applied,
        max_records=max_records,
    )

    if isinstance(response, ExportRequestStatus):
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED, content=response.model_dump()
        )

    return response


@router.get(
    "/provinces",
    summary="Listar provincias con incendios",
    description="Retorna el conteo de incendios por provincia.",
)
def list_provinces(
    service: FireService = Depends(get_fire_service),
):
    provinces = service.list_provinces()
    return {
        "provinces": provinces,
        "total": len(provinces),
    }


@router.get(
    "/{fire_id}",
    response_model=FireDetailResponse,
    summary="Detalle de incendio (público)",
    description="Obtiene detalles de un incendio por ID de evento o episodio. Endpoint público para permitir compartir enlaces.",
)
def get_fire_detail(
    fire_id: UUID,
    service: FireService = Depends(get_fire_service),
) -> FireDetailResponse:
    result = service.get_fire_detail(fire_id)

    if not result:
        result = service.get_fire_detail_from_episode(fire_id)
    if not result:
        raise HTTPException(status_code=404, detail="Evento no encontrado")
    return result


@filters_router.get(
    "/filters",
    response_model=SavedFilterListResponse,
    summary="Listar filtros guardados",
)
def list_saved_filters(
    current_user: User = Depends(require_jwt_user),
    service: FireService = Depends(get_fire_service),
) -> SavedFilterListResponse:
    filters = service.list_saved_filters(current_user.id)
    return SavedFilterListResponse(filters=filters)


@filters_router.post(
    "/filters",
    response_model=SavedFilterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Guardar filtro",
)
def save_filter(
    payload: SavedFilterCreate,
    current_user: User = Depends(require_jwt_user),
    service: FireService = Depends(get_fire_service),
) -> SavedFilterResponse:
    return service.upsert_saved_filter(current_user.id, payload)


@filters_router.delete(
    "/filters/{filter_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar filtro guardado",
)
def delete_filter(
    filter_id: UUID,
    current_user: User = Depends(require_jwt_user),
    service: FireService = Depends(get_fire_service),
):
    deleted = service.delete_saved_filter(current_user.id, filter_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Filtro no encontrado")
    return None
