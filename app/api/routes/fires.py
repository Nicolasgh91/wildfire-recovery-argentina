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
from app.models.evidence import SatelliteImage
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


def apply_fire_filters(
    query,
    *,
    db: Session,
    province: Optional[List[str]] = None,
    department: Optional[str] = None,
    protected_area_id: Optional[UUID] = None,
    in_protected_area: Optional[bool] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    active_only: Optional[bool] = None,
    min_confidence: Optional[float] = None,
    min_detections: Optional[int] = None,
    is_significant: Optional[bool] = None,
    has_imagery: Optional[bool] = None,
    search: Optional[str] = None,
):
    """Aplica filtros comunes a queries de incendios."""
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
        query = query.filter(FireEvent.start_date >= datetime.combine(date_from, datetime.min.time()))

    if date_to:
        query = query.filter(FireEvent.start_date <= datetime.combine(date_to, datetime.max.time()))

    if active_only:
        now = datetime.now()
        query = query.filter(FireEvent.end_date >= now)

    if min_confidence is not None:
        query = query.filter(FireEvent.avg_confidence >= min_confidence)

    if min_detections is not None:
        query = query.filter(FireEvent.total_detections >= min_detections)

    if is_significant is not None:
        query = query.filter(FireEvent.is_significant == is_significant)

    if has_imagery is not None:
        imagery_exists = db.query(SatelliteImage.id).filter(
            SatelliteImage.fire_event_id == FireEvent.id
        ).exists()
        query = query.filter(imagery_exists if has_imagery else ~imagery_exists)

    if search:
        search_term = f"%{search}%"
        query = query.filter(or_(
            FireEvent.province.ilike(search_term),
            FireEvent.department.ilike(search_term),
            ProtectedArea.official_name.ilike(search_term)
        ))

    return query

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
    
    imagery_exists = db.query(SatelliteImage.id).filter(
        SatelliteImage.fire_event_id == FireEvent.id
    ).exists()

    # Query Base con Coordenadas explícitas
    query = db.query(
        FireEvent,
        func.ST_Y(func.cast(FireEvent.centroid, Geometry)).label('lat'),
        func.ST_X(func.cast(FireEvent.centroid, Geometry)).label('lon'),
        imagery_exists.label("has_imagery"),
    )

    # Joins condicionales (si filtramos por protected area)
    if protected_area_id or in_protected_area is not None or search:
        # Join LEFT OUTER para no perder fuegos sin area, 
        # pero si filtramos por area especifica será INNER implícitamente por el WHERE
        query = query.outerjoin(FireProtectedAreaIntersection).outerjoin(ProtectedArea)

    # --- APLICAR FILTROS ---
    query = apply_fire_filters(
        query,
        db=db,
        province=province,
        department=department,
        protected_area_id=protected_area_id,
        in_protected_area=in_protected_area,
        date_from=date_from,
        date_to=date_to,
        active_only=active_only,
        min_confidence=min_confidence,
        min_detections=min_detections,
        is_significant=is_significant,
        has_imagery=has_imagery,
        search=search,
    )
    
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
        fire, lat, lon, has_imagery_result = row
        
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
            has_satellite_imagery=bool(has_imagery_result),
            protected_area_name=pa_name,
            in_protected_area=in_pa
        ))
        
    return FireListResponse(
        fires=results,
        pagination=PaginationMeta.create(total, page, page_size),
        filters_applied=collect_active_filters(
            province=province, department=department, 
            protected_area_id=protected_area_id, in_protected_area=in_protected_area,
            date_from=date_from.isoformat() if date_from else None,
            date_to=date_to.isoformat() if date_to else None,
            active_only=active_only,
            min_confidence=min_confidence,
            min_detections=min_detections,
            is_significant=is_significant,
            has_imagery=has_imagery,
            search=search,
            sort_by=sort_by.value,
            sort_desc=sort_desc,
        )
    )

@router.get(
    "/export",
    summary="Exportar incendios a CSV/JSON",
    description="Exporta lista de incendios filtrada. Máximo 50,000 registros."
)
def export_fires(
    province: Optional[List[str]] = Query(None),
    department: Optional[str] = Query(None),
    protected_area_id: Optional[UUID] = Query(None),
    in_protected_area: Optional[bool] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    active_only: Optional[bool] = Query(None),
    min_confidence: Optional[float] = Query(None, ge=0, le=100),
    min_detections: Optional[int] = Query(None, ge=1),
    is_significant: Optional[bool] = Query(None),
    has_imagery: Optional[bool] = Query(None),
    search: Optional[str] = Query(None, min_length=2, max_length=100),
    format: ExportFormat = Query(ExportFormat.CSV),
    max_records: int = Query(10000, ge=1, le=50000),
    db: Session = Depends(deps.get_db),
) -> StreamingResponse:
    """Exporta incendios a CSV o JSON."""
    
    imagery_exists = db.query(SatelliteImage.id).filter(
        SatelliteImage.fire_event_id == FireEvent.id
    ).exists()

    # Reutilizamos lógica de filtros
    query = db.query(
        FireEvent,
        func.ST_Y(func.cast(FireEvent.centroid, Geometry)).label('lat'),
        func.ST_X(func.cast(FireEvent.centroid, Geometry)).label('lon'),
        imagery_exists.label("has_imagery"),
    )

    if protected_area_id or in_protected_area is not None or search:
        query = query.outerjoin(FireProtectedAreaIntersection).outerjoin(ProtectedArea)

    query = apply_fire_filters(
        query,
        db=db,
        province=province,
        department=department,
        protected_area_id=protected_area_id,
        in_protected_area=in_protected_area,
        date_from=date_from,
        date_to=date_to,
        active_only=active_only,
        min_confidence=min_confidence,
        min_detections=min_detections,
        is_significant=is_significant,
        has_imagery=has_imagery,
        search=search,
    )

    rows = query.limit(max_records).all()
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if format == ExportFormat.CSV:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "id",
            "start_date",
            "end_date",
            "duration_hours",
            "latitude",
            "longitude",
            "province",
            "department",
            "total_detections",
            "avg_confidence",
            "max_frp",
            "estimated_area_hectares",
            "is_significant",
            "has_satellite_imagery",
            "protected_area_name",
            "in_protected_area",
            "status",
        ])
        
        for row in rows:
            fire, lat, lon, has_imagery_result = row
            in_pa = bool(fire.protected_area_intersections)
            pa_name = (
                fire.protected_area_intersections[0].protected_area.official_name
                if in_pa and fire.protected_area_intersections[0].protected_area
                else None
            )
            duration_hours = (
                (fire.end_date - fire.start_date).total_seconds() / 3600
                if fire.end_date and fire.start_date
                else 0
            )
            writer.writerow([
                str(fire.id),
                fire.start_date.isoformat() if fire.start_date else None,
                fire.end_date.isoformat() if fire.end_date else None,
                duration_hours,
                lat,
                lon,
                fire.province,
                fire.department,
                fire.total_detections,
                float(fire.avg_confidence) if fire.avg_confidence else 0,
                float(fire.max_frp) if fire.max_frp else 0,
                float(fire.estimated_area_hectares) if fire.estimated_area_hectares else 0,
                bool(fire.is_significant),
                bool(has_imagery_result),
                pa_name,
                in_pa,
                FireEventListItem(
                    id=fire.id,
                    start_date=fire.start_date,
                    end_date=fire.end_date,
                    total_detections=fire.total_detections or 0,
                ).status.value,
            ])
            
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=fires_{timestamp}.csv"}
        )

    data = {
        "exported_at": datetime.now().isoformat(),
        "total_records": len(rows),
        "filters_applied": collect_active_filters(
            province=province,
            department=department,
            protected_area_id=str(protected_area_id) if protected_area_id else None,
            in_protected_area=in_protected_area,
            date_from=date_from.isoformat() if date_from else None,
            date_to=date_to.isoformat() if date_to else None,
            active_only=active_only,
            min_confidence=min_confidence,
            min_detections=min_detections,
            is_significant=is_significant,
            has_imagery=has_imagery,
            search=search,
        ),
        "fires": [],
    }

    for row in rows:
        fire, lat, lon, has_imagery_result = row
        in_pa = bool(fire.protected_area_intersections)
        pa_name = (
            fire.protected_area_intersections[0].protected_area.official_name
            if in_pa and fire.protected_area_intersections[0].protected_area
            else None
        )
        duration_hours = (
            (fire.end_date - fire.start_date).total_seconds() / 3600
            if fire.end_date and fire.start_date
            else 0
        )
        data["fires"].append({
            "id": str(fire.id),
            "start_date": fire.start_date.isoformat() if fire.start_date else None,
            "end_date": fire.end_date.isoformat() if fire.end_date else None,
            "duration_hours": duration_hours,
            "latitude": lat,
            "longitude": lon,
            "province": fire.province,
            "department": fire.department,
            "total_detections": fire.total_detections,
            "avg_confidence": float(fire.avg_confidence) if fire.avg_confidence else 0,
            "max_frp": float(fire.max_frp) if fire.max_frp else 0,
            "estimated_area_hectares": float(fire.estimated_area_hectares) if fire.estimated_area_hectares else 0,
            "is_significant": bool(fire.is_significant),
            "has_satellite_imagery": bool(has_imagery_result),
            "protected_area_name": pa_name,
            "in_protected_area": in_pa,
            "status": FireEventListItem(
                id=fire.id,
                start_date=fire.start_date,
                end_date=fire.end_date,
                total_detections=fire.total_detections or 0,
            ).status.value,
        })

    filename = f"fires_{timestamp}.json"
    return StreamingResponse(
        iter([json.dumps(data, indent=2, ensure_ascii=False)]),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get(
    "/stats",
    response_model=StatsResponse,
    summary="Estadísticas agregadas",
    tags=["stats"],
)
def get_statistics(
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    province: Optional[List[str]] = Query(None),
    db: Session = Depends(deps.get_db),
):
    filters = []
    if province:
        filters.append(FireEvent.province.in_(province))
    if date_from:
        filters.append(FireEvent.start_date >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        filters.append(FireEvent.start_date <= datetime.combine(date_to, datetime.max.time()))

    summary = db.query(
        func.count(FireEvent.id).label("total_fires"),
        func.coalesce(func.sum(FireEvent.total_detections), 0).label("total_detections"),
        func.coalesce(func.sum(FireEvent.estimated_area_hectares), 0).label("total_hectares"),
        func.coalesce(func.avg(FireEvent.avg_confidence), 0).label("avg_confidence"),
    ).filter(*filters).one()

    by_province_rows = db.query(
        FireEvent.province.label("province"),
        func.count(FireEvent.id).label("fire_count"),
        func.max(FireEvent.start_date).label("latest_fire"),
    ).filter(*filters).group_by(FireEvent.province).all()

    by_month_rows = db.query(
        func.date_trunc("month", FireEvent.start_date).label("month"),
        func.count(FireEvent.id).label("fire_count"),
    ).filter(*filters).group_by(func.date_trunc("month", FireEvent.start_date)).order_by(
        func.date_trunc("month", FireEvent.start_date)
    ).all()

    fires_in_protected = db.query(
        func.count(func.distinct(FireProtectedAreaIntersection.fire_event_id))
    ).join(
        FireEvent,
        FireEvent.id == FireProtectedAreaIntersection.fire_event_id,
    ).filter(*filters).scalar() or 0

    by_province = [
        ProvinceStats(
            name=row.province or "Unknown",
            fire_count=row.fire_count,
            latest_fire=row.latest_fire.date() if row.latest_fire else None,
        )
        for row in by_province_rows
    ]

    by_month = {
        row.month.strftime("%Y-%m"): row.fire_count
        for row in by_month_rows
        if row.month
    }

    return StatsResponse(
        period={
            "from": date_from or date.today(),
            "to": date_to or date.today(),
        },
        stats=FireStatistics(
            total_fires=summary.total_fires,
            total_detections=summary.total_detections,
            total_hectares=float(summary.total_hectares or 0),
            avg_confidence=float(summary.avg_confidence or 0),
            fires_in_protected=fires_in_protected,
            by_province=by_province,
            by_month=by_month,
        )
    )

@router.get(
    "/provinces",
    summary="Lista de provincias"
)
def list_provinces(db: Session = Depends(deps.get_db)):
    """Lista provincias disponibles."""
    results = db.query(
        FireEvent.province,
        func.count(FireEvent.id),
        func.max(FireEvent.start_date),
    ).group_by(FireEvent.province).all()
    return {
        "provinces": [
            {
                "name": r[0] or "Unknown",
                "fire_count": r[1],
                "latest_fire": r[2].date().isoformat() if r[2] else None,
            }
            for r in results
        ],
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
