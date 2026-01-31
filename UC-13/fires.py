"""
API Routes para Fire Events - ForestGuard API.

UC-13: Fire Grid View con filtros, paginación y exportación.

Endpoints:
    GET  /api/v1/fires              - Listar con filtros
    GET  /api/v1/fires/{id}         - Detalle
    GET  /api/v1/fires/export       - Exportar CSV/JSON
    GET  /api/v1/fires/stats        - Estadísticas
    GET  /api/v1/fires/provinces    - Lista de provincias

Autor: ForestGuard Dev Team
Versión: 1.0.0
"""

import csv
import io
import json
import logging
import math
from datetime import date, datetime, timedelta
from typing import Optional, List, Dict, Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func, and_, or_, desc, asc, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

# Local imports
from schemas_fire import (
    FireListResponse,
    FireEventListItem,
    FireDetailResponse,
    FireEventDetail,
    DetectionBrief,
    StatsResponse,
    FireStatistics,
    ProvinceStats,
    PaginationMeta,
    Coordinates,
    ProtectedAreaBrief,
    SortField,
    ExportFormat,
    ExportResult,
)

logger = logging.getLogger(__name__)

# =============================================================================
# ROUTER
# =============================================================================

router = APIRouter(
    prefix="/fires",
    tags=["Fires - UC-13"],
    responses={
        404: {"description": "Incendio no encontrado"},
        422: {"description": "Parámetros inválidos"},
        500: {"description": "Error interno"},
    }
)


# =============================================================================
# DEPENDENCY INJECTION (Placeholder)
# =============================================================================

async def get_db():
    """
    Dependency para obtener sesión de DB.
    En producción, implementar con SQLAlchemy async session.
    """
    # Placeholder - retorna None para modo mock
    yield None


# =============================================================================
# HELPERS
# =============================================================================

def build_sort_clause(sort_by: SortField, sort_desc: bool) -> str:
    """Genera cláusula ORDER BY para SQL."""
    field_map = {
        SortField.START_DATE: "fe.start_date",
        SortField.END_DATE: "fe.end_date",
        SortField.PROVINCE: "fe.province",
        SortField.CONFIDENCE: "fe.avg_confidence",
        SortField.DETECTIONS: "fe.total_detections",
        SortField.FRP: "fe.max_frp",
        SortField.AREA: "fe.estimated_area_hectares",
    }
    field = field_map.get(sort_by, "fe.start_date")
    direction = "DESC NULLS LAST" if sort_desc else "ASC NULLS LAST"
    return f"{field} {direction}"


def collect_active_filters(**kwargs) -> Dict[str, Any]:
    """Recopila filtros activos (no-None) para metadata."""
    return {k: v for k, v in kwargs.items() if v is not None}


# =============================================================================
# MOCK DATA (Para desarrollo sin DB)
# =============================================================================

MOCK_FIRES = [
    FireEventListItem(
        id=UUID("550e8400-e29b-41d4-a716-446655440001"),
        start_date=datetime(2024, 8, 15, 14, 30),
        end_date=datetime(2024, 8, 17, 22, 0),
        duration_hours=55.5,
        centroid=Coordinates(latitude=-28.5432, longitude=-56.1234),
        province="Corrientes",
        department="Santo Tomé",
        total_detections=15,
        avg_confidence=87.5,
        max_frp=245.3,
        estimated_area_hectares=125.5,
        is_significant=True,
        has_satellite_imagery=True,
        has_climate_data=True,
        protected_area_name="Reserva Provincial Iberá",
        in_protected_area=True,
    ),
    FireEventListItem(
        id=UUID("550e8400-e29b-41d4-a716-446655440002"),
        start_date=datetime(2024, 9, 1, 10, 15),
        end_date=datetime(2024, 9, 2, 18, 30),
        duration_hours=32.25,
        centroid=Coordinates(latitude=-26.8765, longitude=-59.4321),
        province="Chaco",
        department="General Güemes",
        total_detections=8,
        avg_confidence=72.3,
        max_frp=156.8,
        estimated_area_hectares=45.2,
        is_significant=False,
        has_satellite_imagery=False,
        has_climate_data=True,
        protected_area_name=None,
        in_protected_area=False,
    ),
    FireEventListItem(
        id=UUID("550e8400-e29b-41d4-a716-446655440003"),
        start_date=datetime(2024, 9, 10, 8, 0),
        end_date=datetime(2024, 9, 12, 16, 45),
        duration_hours=56.75,
        centroid=Coordinates(latitude=-27.1234, longitude=-55.6789),
        province="Misiones",
        department="Iguazú",
        total_detections=23,
        avg_confidence=91.2,
        max_frp=312.5,
        estimated_area_hectares=210.8,
        is_significant=True,
        has_satellite_imagery=True,
        has_climate_data=True,
        protected_area_name="Parque Nacional Iguazú",
        in_protected_area=True,
    ),
    FireEventListItem(
        id=UUID("550e8400-e29b-41d4-a716-446655440004"),
        start_date=datetime(2024, 10, 5, 12, 0),
        end_date=datetime(2024, 10, 6, 20, 0),
        duration_hours=32.0,
        centroid=Coordinates(latitude=-25.3456, longitude=-57.8901),
        province="Formosa",
        department="Pilcomayo",
        total_detections=6,
        avg_confidence=68.5,
        max_frp=98.2,
        estimated_area_hectares=32.1,
        is_significant=False,
        has_satellite_imagery=False,
        has_climate_data=False,
        protected_area_name=None,
        in_protected_area=False,
    ),
    FireEventListItem(
        id=UUID("550e8400-e29b-41d4-a716-446655440005"),
        start_date=datetime(2024, 11, 20, 9, 30),
        end_date=datetime(2024, 11, 23, 14, 0),
        duration_hours=76.5,
        centroid=Coordinates(latitude=-27.8901, longitude=-58.2345),
        province="Corrientes",
        department="Ituzaingó",
        total_detections=42,
        avg_confidence=94.1,
        max_frp=456.7,
        estimated_area_hectares=385.2,
        is_significant=True,
        has_satellite_imagery=True,
        has_climate_data=True,
        protected_area_name="Reserva Provincial Iberá",
        in_protected_area=True,
    ),
]


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get(
    "",
    response_model=FireListResponse,
    summary="Listar incendios con filtros (UC-13)",
    description="""
    Lista eventos de incendio con filtros, paginación y ordenamiento.
    
    ## Filtros disponibles
    - **province**: Filtrar por provincia(s)
    - **department**: Filtrar por departamento
    - **protected_area_id**: Filtrar por área protegida
    - **in_protected_area**: Solo en/fuera de áreas protegidas
    - **date_from / date_to**: Rango de fechas
    - **active_only**: Solo incendios activos
    - **min_confidence**: Confianza mínima (0-100)
    - **min_detections**: Mínimo de detecciones
    - **is_significant**: Solo significativos
    - **has_imagery**: Solo con imágenes satelitales
    - **search**: Búsqueda de texto
    
    ## Ordenamiento
    - **sort_by**: start_date, end_date, province, avg_confidence, total_detections, max_frp, estimated_area_hectares
    - **sort_desc**: true (descendente) / false (ascendente)
    
    ## Paginación
    - **page**: Número de página (desde 1)
    - **page_size**: Items por página (1-100)
    """
)
async def list_fires(
    # Filtros geográficos
    province: Optional[List[str]] = Query(None, description="Provincia(s)"),
    department: Optional[str] = Query(None, description="Departamento"),
    protected_area_id: Optional[UUID] = Query(None, description="ID área protegida"),
    in_protected_area: Optional[bool] = Query(None, description="En área protegida"),
    
    # Filtros temporales
    date_from: Optional[date] = Query(None, description="Fecha desde"),
    date_to: Optional[date] = Query(None, description="Fecha hasta"),
    active_only: Optional[bool] = Query(None, description="Solo activos"),
    
    # Filtros de calidad
    min_confidence: Optional[float] = Query(None, ge=0, le=100, description="Confianza mínima"),
    min_detections: Optional[int] = Query(None, ge=1, description="Mín. detecciones"),
    
    # Filtros de clasificación
    is_significant: Optional[bool] = Query(None, description="Solo significativos"),
    has_imagery: Optional[bool] = Query(None, description="Con imágenes"),
    
    # Búsqueda
    search: Optional[str] = Query(None, min_length=2, max_length=100, description="Buscar"),
    
    # Paginación
    page: int = Query(1, ge=1, description="Página"),
    page_size: int = Query(20, ge=1, le=100, description="Items por página"),
    
    # Ordenamiento
    sort_by: SortField = Query(SortField.START_DATE, description="Ordenar por"),
    sort_desc: bool = Query(True, description="Descendente"),
    
    # DB
    db: Any = Depends(get_db),
) -> FireListResponse:
    """Lista incendios con filtros y paginación."""
    
    logger.info(f"GET /fires - page={page}, province={province}, dates={date_from}-{date_to}")
    
    # Filtrar mock data
    filtered = MOCK_FIRES.copy()
    
    # Aplicar filtros
    if province:
        filtered = [f for f in filtered if f.province in province]
    
    if department:
        filtered = [f for f in filtered if f.department and department.lower() in f.department.lower()]
    
    if in_protected_area is not None:
        filtered = [f for f in filtered if f.in_protected_area == in_protected_area]
    
    if date_from:
        dt_from = datetime.combine(date_from, datetime.min.time())
        filtered = [f for f in filtered if f.start_date >= dt_from]
    
    if date_to:
        dt_to = datetime.combine(date_to, datetime.max.time())
        filtered = [f for f in filtered if f.start_date <= dt_to]
    
    if min_confidence is not None:
        filtered = [f for f in filtered if f.avg_confidence and f.avg_confidence >= min_confidence]
    
    if min_detections is not None:
        filtered = [f for f in filtered if f.total_detections >= min_detections]
    
    if is_significant is not None:
        filtered = [f for f in filtered if f.is_significant == is_significant]
    
    if has_imagery is not None:
        filtered = [f for f in filtered if f.has_satellite_imagery == has_imagery]
    
    if search:
        search_lower = search.lower()
        filtered = [f for f in filtered if 
            (f.province and search_lower in f.province.lower()) or
            (f.department and search_lower in f.department.lower()) or
            (f.protected_area_name and search_lower in f.protected_area_name.lower())
        ]
    
    # Ordenar
    sort_key = {
        SortField.START_DATE: lambda x: x.start_date,
        SortField.END_DATE: lambda x: x.end_date,
        SortField.PROVINCE: lambda x: x.province or "",
        SortField.CONFIDENCE: lambda x: x.avg_confidence or 0,
        SortField.DETECTIONS: lambda x: x.total_detections,
        SortField.FRP: lambda x: x.max_frp or 0,
        SortField.AREA: lambda x: x.estimated_area_hectares or 0,
    }
    filtered.sort(key=sort_key.get(sort_by, sort_key[SortField.START_DATE]), reverse=sort_desc)
    
    # Paginar
    total = len(filtered)
    offset = (page - 1) * page_size
    page_items = filtered[offset:offset + page_size]
    
    # Construir response
    return FireListResponse(
        fires=page_items,
        pagination=PaginationMeta.create(total, page, page_size),
        filters_applied=collect_active_filters(
            province=province,
            department=department,
            protected_area_id=str(protected_area_id) if protected_area_id else None,
            in_protected_area=in_protected_area,
            date_from=date_from.isoformat() if date_from else None,
            date_to=date_to.isoformat() if date_to else None,
            min_confidence=min_confidence,
            min_detections=min_detections,
            is_significant=is_significant,
            has_imagery=has_imagery,
            search=search,
            sort_by=sort_by.value,
            sort_desc=sort_desc,
        ),
    )


@router.get(
    "/export",
    summary="Exportar incendios a CSV/JSON",
    description="Exporta lista de incendios filtrada. Máximo 50,000 registros."
)
async def export_fires(
    # Filtros (mismos que list)
    province: Optional[List[str]] = Query(None),
    department: Optional[str] = Query(None),
    in_protected_area: Optional[bool] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    min_confidence: Optional[float] = Query(None, ge=0, le=100),
    is_significant: Optional[bool] = Query(None),
    
    # Export config
    format: ExportFormat = Query(ExportFormat.CSV),
    max_records: int = Query(10000, ge=1, le=50000),
    
    db: Any = Depends(get_db),
) -> StreamingResponse:
    """Exporta incendios a CSV o JSON."""
    
    logger.info(f"GET /fires/export - format={format}, max={max_records}")
    
    # Aplicar filtros al mock data
    filtered = MOCK_FIRES.copy()
    
    if province:
        filtered = [f for f in filtered if f.province in province]
    if in_protected_area is not None:
        filtered = [f for f in filtered if f.in_protected_area == in_protected_area]
    if date_from:
        dt_from = datetime.combine(date_from, datetime.min.time())
        filtered = [f for f in filtered if f.start_date >= dt_from]
    if date_to:
        dt_to = datetime.combine(date_to, datetime.max.time())
        filtered = [f for f in filtered if f.start_date <= dt_to]
    if min_confidence is not None:
        filtered = [f for f in filtered if f.avg_confidence and f.avg_confidence >= min_confidence]
    if is_significant is not None:
        filtered = [f for f in filtered if f.is_significant == is_significant]
    
    # Limitar registros
    filtered = filtered[:max_records]
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if format == ExportFormat.CSV:
        # Generar CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            "id", "start_date", "end_date", "duration_hours",
            "latitude", "longitude", "province", "department",
            "total_detections", "avg_confidence", "max_frp",
            "estimated_area_ha", "is_significant", "in_protected_area",
            "protected_area_name", "status"
        ])
        
        # Data rows
        for fire in filtered:
            writer.writerow([
                str(fire.id),
                fire.start_date.isoformat(),
                fire.end_date.isoformat(),
                fire.duration_hours,
                fire.centroid.latitude,
                fire.centroid.longitude,
                fire.province,
                fire.department,
                fire.total_detections,
                fire.avg_confidence,
                fire.max_frp,
                fire.estimated_area_hectares,
                fire.is_significant,
                fire.in_protected_area,
                fire.protected_area_name,
                fire.status.value
            ])
        
        output.seek(0)
        filename = f"forestguard_fires_{timestamp}.csv"
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    
    else:
        # JSON format
        data = {
            "exported_at": datetime.now().isoformat(),
            "total_records": len(filtered),
            "fires": [
                {
                    "id": str(f.id),
                    "start_date": f.start_date.isoformat(),
                    "end_date": f.end_date.isoformat(),
                    "duration_hours": f.duration_hours,
                    "latitude": f.centroid.latitude,
                    "longitude": f.centroid.longitude,
                    "province": f.province,
                    "department": f.department,
                    "total_detections": f.total_detections,
                    "avg_confidence": f.avg_confidence,
                    "max_frp": f.max_frp,
                    "estimated_area_hectares": f.estimated_area_hectares,
                    "is_significant": f.is_significant,
                    "in_protected_area": f.in_protected_area,
                    "protected_area_name": f.protected_area_name,
                    "status": f.status.value
                }
                for f in filtered
            ]
        }
        
        filename = f"forestguard_fires_{timestamp}.json"
        
        return StreamingResponse(
            iter([json.dumps(data, indent=2, ensure_ascii=False)]),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )


@router.get(
    "/stats",
    response_model=StatsResponse,
    summary="Estadísticas agregadas de incendios",
    description="Retorna estadísticas agregadas para el período especificado."
)
async def get_statistics(
    date_from: Optional[date] = Query(None, description="Fecha desde"),
    date_to: Optional[date] = Query(None, description="Fecha hasta"),
    province: Optional[List[str]] = Query(None, description="Provincia(s)"),
    db: Any = Depends(get_db),
) -> StatsResponse:
    """Obtiene estadísticas agregadas."""
    
    # Defaults
    if not date_from:
        date_from = date.today() - timedelta(days=365)
    if not date_to:
        date_to = date.today()
    
    # Calcular desde mock data
    filtered = MOCK_FIRES.copy()
    
    if province:
        filtered = [f for f in filtered if f.province in province]
    
    dt_from = datetime.combine(date_from, datetime.min.time())
    dt_to = datetime.combine(date_to, datetime.max.time())
    filtered = [f for f in filtered if dt_from <= f.start_date <= dt_to]
    
    # Calcular estadísticas
    total_fires = len(filtered)
    total_detections = sum(f.total_detections for f in filtered)
    total_hectares = sum(f.estimated_area_hectares or 0 for f in filtered)
    avg_confidence = sum(f.avg_confidence or 0 for f in filtered) / max(total_fires, 1)
    fires_in_protected = sum(1 for f in filtered if f.in_protected_area)
    
    # Por provincia
    province_counts: Dict[str, int] = {}
    for f in filtered:
        if f.province:
            province_counts[f.province] = province_counts.get(f.province, 0) + 1
    
    by_province = [
        ProvinceStats(name=k, fire_count=v)
        for k, v in sorted(province_counts.items(), key=lambda x: -x[1])
    ]
    
    # Por mes
    month_counts: Dict[str, int] = {}
    for f in filtered:
        month_key = f.start_date.strftime("%Y-%m")
        month_counts[month_key] = month_counts.get(month_key, 0) + 1
    
    return StatsResponse(
        period={"from": date_from, "to": date_to},
        stats=FireStatistics(
            total_fires=total_fires,
            total_detections=total_detections,
            total_hectares=total_hectares,
            avg_confidence=round(avg_confidence, 1),
            fires_in_protected=fires_in_protected,
            by_province=by_province,
            by_month=dict(sorted(month_counts.items())),
        ),
    )


@router.get(
    "/provinces",
    summary="Lista de provincias con incendios",
    description="Lista provincias para poblar filtros dropdown."
)
async def list_provinces(
    db: Any = Depends(get_db),
) -> Dict[str, Any]:
    """Lista provincias con conteo de incendios."""
    
    # Calcular desde mock
    province_data: Dict[str, Dict] = {}
    
    for f in MOCK_FIRES:
        if f.province:
            if f.province not in province_data:
                province_data[f.province] = {"count": 0, "latest": None}
            province_data[f.province]["count"] += 1
            if not province_data[f.province]["latest"] or f.start_date > province_data[f.province]["latest"]:
                province_data[f.province]["latest"] = f.start_date
    
    provinces = [
        {
            "name": name,
            "fire_count": data["count"],
            "latest_fire": data["latest"].date().isoformat() if data["latest"] else None
        }
        for name, data in sorted(province_data.items(), key=lambda x: -x[1]["count"])
    ]
    
    return {
        "provinces": provinces,
        "total": len(provinces)
    }


@router.get(
    "/{fire_id}",
    response_model=FireDetailResponse,
    summary="Detalle de un incendio",
    description="Obtiene información completa de un evento de incendio."
)
async def get_fire_detail(
    fire_id: UUID,
    db: Any = Depends(get_db),
) -> FireDetailResponse:
    """Obtiene detalle completo de un incendio."""
    
    logger.info(f"GET /fires/{fire_id}")
    
    # Buscar en mock
    fire = next((f for f in MOCK_FIRES if f.id == fire_id), None)
    
    if not fire:
        raise HTTPException(status_code=404, detail=f"Incendio {fire_id} no encontrado")
    
    # Construir detalle extendido
    detail = FireEventDetail(
        id=fire.id,
        start_date=fire.start_date,
        end_date=fire.end_date,
        duration_hours=fire.duration_hours,
        centroid=fire.centroid,
        province=fire.province,
        department=fire.department,
        total_detections=fire.total_detections,
        avg_confidence=fire.avg_confidence,
        max_frp=fire.max_frp,
        avg_frp=fire.max_frp * 0.65 if fire.max_frp else None,
        sum_frp=fire.max_frp * fire.total_detections * 0.5 if fire.max_frp else None,
        estimated_area_hectares=fire.estimated_area_hectares,
        is_significant=fire.is_significant,
        has_satellite_imagery=fire.has_satellite_imagery,
        has_climate_data=fire.has_climate_data,
        has_legal_analysis=False,
        processing_error=None,
        protected_area_name=fire.protected_area_name,
        in_protected_area=fire.in_protected_area,
        protected_areas=[
            ProtectedAreaBrief(
                id=UUID("770e8400-e29b-41d4-a716-446655440010"),
                name=fire.protected_area_name,
                category="provincial_reserve",
                prohibition_until=date(2084, 8, 15)
            )
        ] if fire.protected_area_name else [],
        created_at=fire.start_date - timedelta(hours=1),
        updated_at=fire.end_date + timedelta(hours=2),
    )
    
    # Mock detections
    detections = [
        DetectionBrief(
            id=UUID("880e8400-e29b-41d4-a716-446655440020"),
            satellite="VIIRS",
            detected_at=fire.start_date,
            latitude=fire.centroid.latitude,
            longitude=fire.centroid.longitude,
            frp=fire.max_frp,
            confidence=int(fire.avg_confidence) if fire.avg_confidence else None,
        ),
        DetectionBrief(
            id=UUID("880e8400-e29b-41d4-a716-446655440021"),
            satellite="VIIRS",
            detected_at=fire.start_date + timedelta(hours=6),
            latitude=fire.centroid.latitude + 0.001,
            longitude=fire.centroid.longitude - 0.001,
            frp=(fire.max_frp or 100) * 0.8,
            confidence=int((fire.avg_confidence or 70) - 5),
        ),
    ]
    
    return FireDetailResponse(
        fire=detail,
        detections=detections,
        related_fires_count=2
    )


# =============================================================================
# HEALTH CHECK
# =============================================================================

@router.get("/health", include_in_schema=False)
async def health():
    """Health check del servicio."""
    return {
        "service": "fires",
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "mock_data_count": len(MOCK_FIRES)
    }