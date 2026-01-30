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
from sqlalchemy.orm import Session, joinedload
from geoalchemy2 import Geometry

# Local imports
from app.api import deps
from app.models.fire import FireEvent, FireDetection
from app.models.region import FireProtectedAreaIntersection, ProtectedArea
from app.schemas.fire import (
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
    FireStatus, 
)

logger = logging.getLogger(__name__)

router = APIRouter()

# =============================================================================
# HELPERS
# =============================================================================

def build_sort_clause(sort_by: SortField, sort_desc: bool):
    """Genera cláusula ORDER BY para SQLAlchemy."""
    field_map = {
        SortField.START_DATE: FireEvent.start_date,
        SortField.END_DATE: FireEvent.end_date,
        SortField.PROVINCE: FireEvent.province,
        SortField.CONFIDENCE: FireEvent.avg_confidence,
        SortField.DETECTIONS: FireEvent.total_detections,
        SortField.FRP: FireEvent.max_frp,
        SortField.AREA: FireEvent.estimated_area_hectares,
    }
    field = field_map.get(sort_by, FireEvent.start_date)
    return desc(field) if sort_desc else asc(field)

def collect_active_filters(**kwargs) -> Dict[str, Any]:
    """Recopila filtros activos (no-None) para metadata."""
    return {k: v for k, v in kwargs.items() if v is not None}

def to_coordinates(geom_wkb) -> Optional[Dict[str, float]]:
    """Convierte WKBElement a dict {latitude, longitude} (Simplificado)."""
    # Nota: GeoAlchemy2 devuelve WKBElement. Para leerlo fácil necesitamos func.ST_X / ST_Y en query
    # O usar shapely. Por performance en listados, mejor pedir coords en la query.
    # Aquí asumiremos que el modelo ya se hidrata. Si no, retornamos None o placeholder.
    # Como FireEvent model no tiene lat/lon como columnas property simple, esto es complejo sin query específica.
    # SOLUCIÓN: Usaremos ST_AsGeoJSON o ST_X/Y en la query principal si fuera performance crítica.
    # Para MVP, si el objeto FireEvent no tiene lat/lon, usamos Mock o 0.
    # REVISAR MODELO: App/Model/Fire parece no tener lat/lon directos, solo centroid (Geography).
    # Vamos a confiar en que la app ya maneja esto o agregaremos propiedades híbridas en el futuro.
    return None 

# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get(
    "/",
    response_model=FireListResponse,
    summary="Listar incendios con filtros (UC-13)",
    description="Lista eventos de incendio con filtros, paginación y ordenamiento."
)
def list_fires(
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
    has_imagery: Optional[bool] = Query(None, description="Con imágenes (mock, no implemented in DB yet)"),
    
    # Búsqueda
    search: Optional[str] = Query(None, min_length=2, max_length=100, description="Buscar"),
    
    # Paginación
    page: int = Query(1, ge=1, description="Página"),
    page_size: int = Query(20, ge=1, le=100, description="Items por página"),
    
    # Ordenamiento
    sort_by: SortField = Query(SortField.START_DATE, description="Ordenar por"),
    sort_desc: bool = Query(True, description="Descendente"),
    
    db: Session = Depends(deps.get_db),
) -> FireListResponse:
    """Lista incendios con filtros y paginación."""
    
    # Query Base con Coordenadas explícitas
    query = db.query(
        FireEvent,
        func.ST_Y(func.cast(FireEvent.centroid, Geometry)).label('lat'),
        func.ST_X(func.cast(FireEvent.centroid, Geometry)).label('lon')
    )

    # Joins condicionales (si filtramos por protected area)
    if protected_area_id or in_protected_area is not None or search:
        # Join LEFT OUTER para no perder fuegos sin area, 
        # pero si filtramos por area especifica será INNER implícitamente por el WHERE
        query = query.outerjoin(FireProtectedAreaIntersection).outerjoin(ProtectedArea)

    # --- APLICAR FILTROS ---
    
    if province:
        query = query.filter(FireEvent.province.in_(province))
    
    if department:
        query = query.filter(FireEvent.department.ilike(f"%{department}%"))
        
    if protected_area_id:
        query = query.filter(FireProtectedAreaIntersection.protected_area_id == protected_area_id)
        
    if in_protected_area is not None:
        if in_protected_area:
            query = query.filter(FireProtectedAreaIntersection.id.isnot(None))
        else:
            query = query.filter(FireProtectedAreaIntersection.id.is_(None))
            
    if date_from:
        query = query.filter(FireEvent.start_date >= date_from)
        
    if date_to:
        query = query.filter(FireEvent.start_date <= date_to) # Asume timestamps
        
    if active_only:
        # Lógica aproximada: End Date en futuro o muy reciente (< 24h)
        now = datetime.now()
        query = query.filter(FireEvent.end_date >= now)

    if min_confidence:
        query = query.filter(FireEvent.avg_confidence >= min_confidence)
        
    if min_detections:
        query = query.filter(FireEvent.total_detections >= min_detections)
        
    if is_significant is not None:
        query = query.filter(FireEvent.is_significant == is_significant)
        
    if search:
        search_term = f"%{search}%"
        query = query.filter(or_(
            FireEvent.province.ilike(search_term),
            FireEvent.department.ilike(search_term),
            ProtectedArea.official_name.ilike(search_term)
        ))
    
    # --- TOTAL COUNT (para paginación) ---
    # Optimizacion: Count sobre subquery o id
    total = query.with_entities(func.count(FireEvent.id)).scalar()
    
    # --- ORDENAMIENTO ---
    query = query.order_by(build_sort_clause(sort_by, sort_desc))
    
    # --- PAGINACIÓN ---
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    
    # --- MAPEO A SCHEMA ---
    results = []
    for row in items:
        fire, lat, lon = row
        
        # Determinar nombre area protegida (si existe intersección)
        # Esto es n+1 potential issue, pero aceptable para page_size=20
        # Idealmente vendría del join
        pa_name = None
        in_pa = False
        if fire.protected_area_intersections:
             pa_name = fire.protected_area_intersections[0].protected_area.official_name if fire.protected_area_intersections and fire.protected_area_intersections[0].protected_area else None
             in_pa = True

        results.append(FireEventListItem(
            id=fire.id,
            start_date=fire.start_date,
            end_date=fire.end_date,
            duration_hours=(fire.end_date - fire.start_date).total_seconds() / 3600 if fire.end_date and fire.start_date else 0,
            centroid={"latitude": float(lat) if lat else 0, "longitude": float(lon) if lon else 0},
            province=fire.province,
            department=fire.department,
            total_detections=fire.total_detections or 0,
            avg_confidence=float(fire.avg_confidence) if fire.avg_confidence else 0,
            max_frp=float(fire.max_frp) if fire.max_frp else 0,
            estimated_area_hectares=float(fire.estimated_area_hectares) if fire.estimated_area_hectares else 0,
            is_significant=fire.is_significant or False,
            protected_area_name=pa_name,
            in_protected_area=in_pa
        ))
        
    return FireListResponse(
        fires=results,
        pagination=PaginationMeta.create(total, page, page_size),
        filters_applied=collect_active_filters(
            province=province, department=department, 
            protected_area_id=protected_area_id, in_protected_area=in_protected_area,
            min_confidence=min_confidence, is_significant=is_significant
        )
    )

@router.get(
    "/export",
    summary="Exportar incendios a CSV/JSON",
    description="Exporta lista de incendios filtrada. Máximo 50,000 registros."
)
def export_fires(
    province: Optional[List[str]] = Query(None),
    is_significant: Optional[bool] = Query(None),
    format: ExportFormat = Query(ExportFormat.CSV),
    max_records: int = Query(10000, ge=1, le=50000),
    db: Session = Depends(deps.get_db),
) -> StreamingResponse:
    """Exporta incendios a CSV o JSON."""
    
    # Reutilizamos lógica de filtros (simplificada)
    query = db.query(
        FireEvent,
        func.ST_Y(func.cast(FireEvent.centroid, Geometry)).label('lat'),
        func.ST_X(func.cast(FireEvent.centroid, Geometry)).label('lon')
    )
    
    if province: query = query.filter(FireEvent.province.in_(province))
    if is_significant is not None: query = query.filter(FireEvent.is_significant == is_significant)
    
    rows = query.limit(max_records).all()
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if format == ExportFormat.CSV:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["id", "start_date", "province", "lat", "lon", "detections", "hectares"])
        
        for r in rows:
            fire, lat, lon = r
            writer.writerow([
                str(fire.id), fire.start_date, fire.province, 
                lat, lon, fire.total_detections, fire.estimated_area_hectares
            ])
            
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=fires_{timestamp}.csv"}
        )
    
    # JSON impl...
    return StreamingResponse(iter(["Not implemented"]), media_type="application/json")


@router.get(
    "/stats",
    response_model=StatsResponse,
    summary="Estadísticas agregadas"
)
def get_statistics(
    date_from: Optional[date] = Query(None),
    province: Optional[List[str]] = Query(None),
    db: Session = Depends(deps.get_db),
):
    query = db.query(FireEvent)
    if province: query = query.filter(FireEvent.province.in_(province))
    if date_from: query = query.filter(FireEvent.start_date >= date_from)
    
    total = query.count()
    # Mock aggregates for MVP
    return StatsResponse(
        period={"from": date_from or date.today()},
        stats=FireStatistics(
            total_fires=total,
            total_detections=0,
            total_hectares=0,
            avg_confidence=0,
            fires_in_protected=0,
            by_province=[],
            by_month={}
        )
    )

@router.get(
    "/provinces",
    summary="Lista de provincias"
)
def list_provinces(db: Session = Depends(deps.get_db)):
    """Lista provincias disponibles."""
    results = db.query(FireEvent.province, func.count(FireEvent.id)).group_by(FireEvent.province).all()
    return {
        "provinces": [{"name": r[0] or "Unknown", "fire_count": r[1]} for r in results],
        "total": len(results)
    }

@router.get(
    "/{fire_id}",
    response_model=FireDetailResponse,
    summary="Detalle de un incendio"
)
def read_fire_detail(
    fire_id: UUID,
    db: Session = Depends(deps.get_db)
):
    # Query con lat/lon y joins necesarios
    row = db.query(
        FireEvent,
        func.ST_Y(func.cast(FireEvent.centroid, Geometry)).label('lat'),
        func.ST_X(func.cast(FireEvent.centroid, Geometry)).label('lon')
    ).filter(FireEvent.id == fire_id).first()
    
    if not row:
        raise HTTPException(status_code=404, detail="Incendio no encontrado")
        
    fire, lat, lon = row
    
    # Construir detail response
    # (Simplified for MVP integration)
    detail = FireEventDetail(
        id=fire.id,
        start_date=fire.start_date,
        end_date=fire.end_date,
        centroid={"latitude": lat, "longitude": lon},
        total_detections=fire.total_detections or 0,
        province=fire.province, is_significant=fire.is_significant or False,
        created_at=fire.created_at
    )
    
    return FireDetailResponse(fire=detail, detections=[], related_fires_count=0)
