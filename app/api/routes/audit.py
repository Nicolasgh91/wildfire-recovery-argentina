"""
=============================================================================
FORESTGUARD API - ENDPOINTS DE AUDITORÍA (UC-01)
=============================================================================

Endpoint principal para verificar si un terreno tiene restricciones legales
por incendios previos según la Ley 26.815 Art. 22 bis.

Casos de uso:
- Escribanos verificando terrenos antes de escriturar
- Compradores verificando antes de comprar
- Inspectores municipales verificando permisos de construcción
- Ciudadanos verificando su propiedad

Flujo del endpoint /audit/land-use:
-----------------------------------
1. Recibe coordenadas (lat, lon) y radio de búsqueda
2. Busca fire_events cercanos usando ST_DWithin (índice GIST)
3. Para cada incendio, verifica si hay intersección con área protegida
4. Calcula la fecha de prohibición más lejana
5. Genera un resumen legal claro
6. Registra la auditoría para trazabilidad

Marco Legal:
------------
Ley 26.815 Art. 22 bis prohíbe cambio de uso del suelo:
- 60 años: Bosques nativos y áreas protegidas
- 30 años: Zonas agrícolas/praderas

Autor: ForestGuard Team
Fecha: 2025-01
=============================================================================
"""

import time
from datetime import date, datetime, timedelta
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import text
from sqlalchemy.orm import Session

# Ajustar imports según tu estructura
try:
    from app.db.session import get_db
except ImportError:
    from app.api.deps import get_db

from app.core.rate_limiter import check_rate_limit


# =============================================================================
# ROUTER
# =============================================================================

router = APIRouter()


# =============================================================================
# SCHEMAS
# =============================================================================

class GeoPoint(BaseModel):
    """Punto geográfico con coordenadas."""
    lat: float = Field(..., ge=-90, le=90, description="Latitud en grados decimales")
    lon: float = Field(..., ge=-180, le=180, description="Longitud en grados decimales")


class AuditRequest(BaseModel):
    """
    Request para auditoría de uso del suelo.
    
    Ejemplo:
        {
            "lat": -27.4658,
            "lon": -58.8346,
            "radius_meters": 500,
            "cadastral_id": "CHA-123-456"
        }
    """
    lat: float = Field(
        ..., 
        ge=-56, le=-21,  # Límites de Argentina
        description="Latitud del punto a consultar",
        examples=[-27.4658]
    )
    lon: float = Field(
        ..., 
        ge=-74, le=-53,  # Límites de Argentina
        description="Longitud del punto a consultar",
        examples=[-58.8346]
    )
    radius_meters: int = Field(
        default=500,
        ge=100, le=5000,
        description="Radio de búsqueda en metros (100-5000)"
    )
    cadastral_id: Optional[str] = Field(
        default=None,
        description="ID catastral del terreno (opcional)"
    )
    
    @field_validator('lat')
    @classmethod
    def validate_lat_argentina(cls, v):
        """Valida que la latitud esté dentro de Argentina."""
        if not (-56 <= v <= -21):
            raise ValueError('Latitud fuera del territorio argentino (-56 a -21)')
        return v
    
    @field_validator('lon')
    @classmethod
    def validate_lon_argentina(cls, v):
        """Valida que la longitud esté dentro de Argentina."""
        if not (-74 <= v <= -53):
            raise ValueError('Longitud fuera del territorio argentino (-74 a -53)')
        return v


class FireInAudit(BaseModel):
    """Incendio encontrado en la auditoría."""
    fire_event_id: UUID
    fire_date: date
    province: Optional[str] = None
    estimated_area_hectares: Optional[float] = None
    avg_confidence: Optional[float] = None
    in_protected_area: bool
    protected_area_name: Optional[str] = None
    protected_area_category: Optional[str] = None
    prohibition_until: date
    years_remaining: int
    distance_meters: float


class ProtectedAreaInAudit(BaseModel):
    """Área protegida cercana al punto consultado."""
    protected_area_id: UUID
    official_name: str
    category: str
    distance_meters: float
    prohibition_years: int


class AuditResponse(BaseModel):
    """
    Response de la auditoría de uso del suelo.
    
    Campos clave:
    - is_prohibited: Si el terreno tiene restricción vigente
    - prohibition_until: Fecha hasta la cual aplica la restricción
    - violation_severity: Gravedad (critical, high, medium, low, none)
    """
    # Metadata de la consulta
    audit_id: UUID
    queried_at: datetime
    query_duration_ms: int
    
    # Ubicación consultada
    location: GeoPoint
    radius_meters: int
    cadastral_id: Optional[str] = None
    
    # Resultados principales
    fires_found: int
    is_prohibited: bool
    prohibition_until: Optional[date] = None
    violation_severity: str  # critical, high, medium, low, none
    
    # Detalle de incendios
    fires: List[FireInAudit]
    
    # Áreas protegidas cercanas
    protected_areas_nearby: List[ProtectedAreaInAudit]
    
    # Resumen legal (texto descriptivo)
    legal_summary: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "audit_id": "550e8400-e29b-41d4-a716-446655440000",
                "queried_at": "2025-01-25T14:30:00Z",
                "query_duration_ms": 245,
                "location": {"lat": -27.4658, "lon": -58.8346},
                "radius_meters": 500,
                "cadastral_id": None,
                "fires_found": 2,
                "is_prohibited": True,
                "prohibition_until": "2075-08-22",
                "violation_severity": "critical",
                "fires": [],
                "protected_areas_nearby": [],
                "legal_summary": "⚠️ TERRENO CON RESTRICCIÓN LEGAL..."
            }
        }


# =============================================================================
# FUNCIONES AUXILIARES
# =============================================================================

def calculate_violation_severity(years_remaining: int) -> str:
    """
    Calcula la severidad de la violación basada en años restantes.
    
    Args:
        years_remaining: Años hasta que expire la prohibición
        
    Returns:
        str: Nivel de severidad
    """
    if years_remaining <= 0:
        return "none"
    elif years_remaining > 50:
        return "critical"  # Más de 50 años = muy reciente
    elif years_remaining > 30:
        return "high"
    elif years_remaining > 10:
        return "medium"
    else:
        return "low"


def generate_legal_summary(
    fires_found: int,
    is_prohibited: bool,
    prohibition_until: Optional[date],
    years_remaining: int,
    protected_area_name: Optional[str]
) -> str:
    """
    Genera un resumen legal en lenguaje natural.
    
    Args:
        fires_found: Cantidad de incendios encontrados
        is_prohibited: Si hay prohibición activa
        prohibition_until: Fecha de fin de prohibición
        years_remaining: Años restantes
        protected_area_name: Nombre del área protegida (si aplica)
        
    Returns:
        str: Resumen en español
    """
    if fires_found == 0:
        return (
            "✅ NO SE ENCONTRARON INCENDIOS en el área consultada. "
            "El terreno no presenta restricciones por la Ley 26.815 según los registros "
            "satelitales disponibles (2015-presente)."
        )
    
    if not is_prohibited:
        return (
            f"ℹ️ Se encontraron {fires_found} incendio(s) histórico(s), pero las restricciones "
            "legales ya expiraron. El terreno NO tiene prohibiciones vigentes por la Ley 26.815."
        )
    
    # Hay prohibición activa
    area_info = f" dentro del {protected_area_name}" if protected_area_name else ""
    
    return (
        f"⚠️ TERRENO CON RESTRICCIÓN LEGAL. "
        f"Se detectaron {fires_found} incendio(s){area_info}. "
        f"Según la Ley 26.815 Art. 22 bis, está PROHIBIDO el cambio de uso del suelo "
        f"(loteo, construcción, agricultura) hasta el {prohibition_until.strftime('%d/%m/%Y')} "
        f"({years_remaining} años restantes). "
        f"Cualquier transacción inmobiliaria debe considerar esta restricción."
    )


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post(
    "/land-use",
    response_model=AuditResponse,
    summary="Auditoría de uso del suelo",
    description="""
    Verifica si un terreno tiene restricciones legales por incendios previos.
    
    **Ley 26.815 Art. 22 bis** prohíbe cambio de uso del suelo:
    - **60 años** para bosques nativos y áreas protegidas
    - **30 años** para zonas agrícolas/praderas
    Realiza una auditoría legal completa para un punto geográfico.
    Detecta historial de incendios y prohibiciones activas de venta/edificación.
    """,
    dependencies=[Depends(check_rate_limit)]
)
async def audit_land_use(
    request: AuditRequest,
    http_request: Request,
    db: Session = Depends(get_db)
) -> AuditResponse:
    """
    Realiza una auditoría de uso del suelo para las coordenadas especificadas.
    
    Flujo:
    1. Busca incendios cercanos (ST_DWithin)
    2. Verifica intersecciones con áreas protegidas pre-calculadas
    3. Calcula prohibiciones y severidad
    4. Registra la auditoría para trazabilidad
    5. Retorna resultado con resumen legal
    """
    start_time = time.time()
    
    try:
        # ---------------------------------------------------------------------
        # 1. Buscar incendios cercanos
        # ---------------------------------------------------------------------
        fires_query = text("""
            SELECT 
                fe.id as fire_event_id,
                fe.start_date as fire_date,
                fe.province,
                fe.estimated_area_hectares,
                fe.avg_confidence,
                ST_Distance(
                    fe.centroid::geography,
                    ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
                ) as distance_meters,
                -- Información de intersección con área protegida (si existe)
                fpa.protected_area_id,
                fpa.prohibition_until,
                pa.official_name as protected_area_name,
                pa.category as protected_area_category,
                pa.prohibition_years
            FROM fire_events fe
            LEFT JOIN fire_protected_area_intersections fpa ON fpa.fire_event_id = fe.id
            LEFT JOIN protected_areas pa ON pa.id = fpa.protected_area_id
            WHERE ST_DWithin(
                fe.centroid::geography,
                ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
                :radius
            )
            ORDER BY fe.start_date DESC
        """)
        
        fires_result = db.execute(fires_query, {
            "lat": request.lat,
            "lon": request.lon,
            "radius": request.radius_meters
        }).fetchall()
        
        # ---------------------------------------------------------------------
        # 2. Buscar áreas protegidas cercanas (independiente de incendios)
        # ---------------------------------------------------------------------
        # Corrección: DISTINCT ON para evitar duplicados del mismo parque
        areas_query = text("""
            SELECT DISTINCT ON (pa.official_name)
                pa.id as protected_area_id,
                pa.official_name,
                pa.category,
                pa.prohibition_years,
                ST_Distance(
                    pa.boundary::geography,
                    ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
                ) as distance_meters
            FROM protected_areas pa
            WHERE ST_DWithin(
                pa.boundary::geography,
                ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
                :radius
            )
            ORDER BY pa.official_name, distance_meters ASC
            LIMIT 5
        """)
        
        areas_result = db.execute(areas_query, {
            "lat": request.lat,
            "lon": request.lon,
            "radius": request.radius_meters * 2
        }).fetchall()
        
        # ---------------------------------------------------------------------
        # 3. Procesar resultados
        # ---------------------------------------------------------------------
        fires: List[FireInAudit] = []
        max_prohibition_until: Optional[date] = None
        max_years_remaining = 0
        latest_protected_area_name: Optional[str] = None
        
        # Usar un set para evitar duplicados
        seen_fire_ids = set()
        
        for row in fires_result:
            fire_id = str(row.fire_event_id)
            
            # Evitar duplicados
            if fire_id in seen_fire_ids:
                continue
            seen_fire_ids.add(fire_id)
            
            # Determinar prohibición
            in_protected_area = row.protected_area_id is not None
            
            if in_protected_area and row.prohibition_until:
                prohibition_until = row.prohibition_until
                years_remaining = max(0, (prohibition_until - date.today()).days // 365)
            else:
                # Incendio fuera de área protegida: 30 años por defecto
                fire_date_val = row.fire_date.date() if hasattr(row.fire_date, 'date') else row.fire_date
                prohibition_until = fire_date_val + timedelta(days=30 * 365)
                years_remaining = max(0, (prohibition_until - date.today()).days // 365)
            
            # Actualizar máximo
            if max_prohibition_until is None or prohibition_until > max_prohibition_until:
                max_prohibition_until = prohibition_until
                max_years_remaining = years_remaining
                latest_protected_area_name = row.protected_area_name
            
            fires.append(FireInAudit(
                fire_event_id=row.fire_event_id,
                fire_date=row.fire_date.date() if hasattr(row.fire_date, 'date') else row.fire_date,
                province=row.province,
                estimated_area_hectares=row.estimated_area_hectares,
                avg_confidence=row.avg_confidence,
                in_protected_area=in_protected_area,
                protected_area_name=row.protected_area_name,
                protected_area_category=row.protected_area_category,
                prohibition_until=prohibition_until,
                years_remaining=years_remaining,
                distance_meters=round(row.distance_meters, 1)
            ))
        
        # Procesar áreas protegidas
        protected_areas: List[ProtectedAreaInAudit] = [
            ProtectedAreaInAudit(
                protected_area_id=row.protected_area_id,
                official_name=row.official_name,
                category=row.category,
                distance_meters=round(row.distance_meters, 1),
                prohibition_years=row.prohibition_years
            )
            for row in areas_result
        ]
        
        # ---------------------------------------------------------------------
        # 4. Calcular resultado final
        # ---------------------------------------------------------------------
        fires_found = len(fires)
        is_prohibited = max_prohibition_until is not None and max_prohibition_until > date.today()
        violation_severity = calculate_violation_severity(max_years_remaining)
        
        legal_summary = generate_legal_summary(
            fires_found=fires_found,
            is_prohibited=is_prohibited,
            prohibition_until=max_prohibition_until,
            years_remaining=max_years_remaining,
            protected_area_name=latest_protected_area_name
        )
        
        # ---------------------------------------------------------------------
        # 5. Registrar auditoría
        # ---------------------------------------------------------------------
        query_duration_ms = int((time.time() - start_time) * 1000)
        
        audit_insert = text("""
            INSERT INTO land_use_audits (
                id,
                queried_latitude,
                queried_longitude,
                queried_location,
                search_radius_meters,
                queried_at,
                fires_found,
                earliest_fire_date,
                latest_fire_date,
                prohibition_until,
                is_violation,
                violation_severity,
                user_ip,
                user_agent,
                query_duration_ms,
                created_at
            ) VALUES (
                gen_random_uuid(),
                :lat,
                :lon,
                ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
                :radius,
                NOW(),
                :fires_found,
                :earliest_fire_date,
                :latest_fire_date,
                :prohibition_until,
                :is_violation,
                :violation_severity,
                :user_ip,
                :user_agent,
                :query_duration_ms,
                NOW()
            )
            RETURNING id
        """)
        
        # Obtener fechas extremas
        fire_dates = [f.fire_date for f in fires]
        earliest_fire = min(fire_dates) if fire_dates else None
        latest_fire = max(fire_dates) if fire_dates else None
        
        # Obtener IP del cliente
        client_ip = http_request.client.host if http_request.client else None
        user_agent = http_request.headers.get("user-agent", "")[:500]
        
        audit_result = db.execute(audit_insert, {
            "lat": request.lat,
            "lon": request.lon,
            "radius": request.radius_meters,
            "fires_found": fires_found,
            "earliest_fire_date": earliest_fire,
            "latest_fire_date": latest_fire,
            "prohibition_until": max_prohibition_until,
            "is_violation": is_prohibited,
            "violation_severity": violation_severity,
            "user_ip": client_ip,
            "user_agent": user_agent,
            "query_duration_ms": query_duration_ms
        })
        
        audit_id = audit_result.fetchone()[0]
        db.commit()
        
        # ---------------------------------------------------------------------
        # 6. Retornar respuesta
        # ---------------------------------------------------------------------
        return AuditResponse(
            audit_id=audit_id,
            queried_at=datetime.utcnow(),
            query_duration_ms=query_duration_ms,
            location=GeoPoint(lat=request.lat, lon=request.lon),
            radius_meters=request.radius_meters,
            cadastral_id=request.cadastral_id,
            fires_found=fires_found,
            is_prohibited=is_prohibited,
            prohibition_until=max_prohibition_until,
            violation_severity=violation_severity,
            fires=fires,
            protected_areas_nearby=protected_areas,
            legal_summary=legal_summary
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error procesando auditoría: {str(e)}"
        )


@router.get(
    "/{audit_id}",
    response_model=AuditResponse,
    summary="Obtener auditoría por ID",
    description="Recupera los detalles de una auditoría previamente realizada."
)
async def get_audit(
    audit_id: UUID,
    db: Session = Depends(get_db)
) -> AuditResponse:
    """
    Recupera una auditoría existente por su ID.
    
    Útil para:
    - Verificar auditorías anteriores
    - Generar reportes o certificados basados en auditorías
    """
    query = text("""
        SELECT 
            id,
            queried_latitude,
            queried_longitude,
            search_radius_meters,
            queried_at,
            fires_found,
            prohibition_until,
            is_violation,
            violation_severity,
            query_duration_ms
        FROM land_use_audits
        WHERE id = :audit_id
    """)
    
    result = db.execute(query, {"audit_id": str(audit_id)}).fetchone()
    
    if not result:
        raise HTTPException(status_code=404, detail="Auditoría no encontrada")
    
    # Reconstruir la respuesta (simplificada)
    return AuditResponse(
        audit_id=result.id,
        queried_at=result.queried_at,
        query_duration_ms=result.query_duration_ms or 0,
        location=GeoPoint(lat=result.queried_latitude, lon=result.queried_longitude),
        radius_meters=result.search_radius_meters,
        cadastral_id=None,
        fires_found=result.fires_found,
        is_prohibited=result.is_violation,
        prohibition_until=result.prohibition_until,
        violation_severity=result.violation_severity or "none",
        fires=[],
        protected_areas_nearby=[],
        legal_summary=f"Auditoría #{result.id} realizada el {result.queried_at.strftime('%d/%m/%Y %H:%M')}"
    )
