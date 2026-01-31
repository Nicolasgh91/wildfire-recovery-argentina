"""
Schemas Pydantic para Fire Events - ForestGuard API.

UC-13: Fire Grid View con filtros, paginación y exportación.

Autor: ForestGuard Dev Team
Versión: 1.0.0
"""

from datetime import date, datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from uuid import UUID
from pydantic import BaseModel, Field, computed_field
import math


# =============================================================================
# ENUMS
# =============================================================================

class FireStatus(str, Enum):
    """Estados de un evento de incendio."""
    ACTIVE = "active"
    CONTROLLED = "controlled"
    EXTINGUISHED = "extinguished"
    MONITORING = "monitoring"

class SortField(str, Enum):
    """Campos permitidos para ordenamiento."""
    START_DATE = "start_date"
    END_DATE = "end_date"
    PROVINCE = "province"
    CONFIDENCE = "avg_confidence"
    DETECTIONS = "total_detections"
    FRP = "max_frp"
    AREA = "estimated_area_hectares"

class ExportFormat(str, Enum):
    """Formatos de exportación."""
    CSV = "csv"
    JSON = "json"


# =============================================================================
# RESPONSE MODELS
# =============================================================================

class Coordinates(BaseModel):
    """Coordenadas geográficas."""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


class ProtectedAreaBrief(BaseModel):
    """Resumen de área protegida."""
    id: UUID
    name: str
    category: str
    prohibition_until: Optional[date] = None


class FireEventListItem(BaseModel):
    """
    Item de la grilla de incendios (UC-13).
    Versión ligera optimizada para listados.
    """
    id: UUID
    
    # Temporal
    start_date: datetime
    end_date: datetime
    duration_hours: Optional[float] = None
    
    # Ubicación
    centroid: Coordinates
    province: Optional[str] = None
    department: Optional[str] = None
    
    # Métricas
    total_detections: int
    avg_confidence: Optional[float] = Field(None, ge=0, le=100)
    max_frp: Optional[float] = None
    estimated_area_hectares: Optional[float] = None
    
    # Estado
    is_significant: bool = False
    has_satellite_imagery: bool = False
    has_climate_data: bool = False
    
    # Área protegida
    protected_area_name: Optional[str] = None
    in_protected_area: bool = False
    
    @computed_field
    @property
    def status(self) -> FireStatus:
        """Calcula estado basado en temporalidad."""
        now = datetime.now()
        if self.end_date > now:
            return FireStatus.ACTIVE
        days = (now - self.end_date).days
        if days < 3:
            return FireStatus.CONTROLLED
        elif days < 14:
            return FireStatus.MONITORING
        return FireStatus.EXTINGUISHED

    class Config:
        from_attributes = True


class PaginationMeta(BaseModel):
    """Metadata de paginación."""
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool
    
    @classmethod
    def create(cls, total: int, page: int, page_size: int) -> "PaginationMeta":
        """Factory method para crear metadata."""
        total_pages = math.ceil(total / page_size) if page_size > 0 else 0
        return cls(
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1
        )


class FireListResponse(BaseModel):
    """
    Response del listado de incendios (UC-13).
    """
    fires: List[FireEventListItem]
    pagination: PaginationMeta
    filters_applied: Dict[str, Any] = {}
    generated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        json_schema_extra = {
            "example": {
                "fires": [{
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "start_date": "2024-08-15T14:30:00Z",
                    "end_date": "2024-08-17T22:00:00Z",
                    "centroid": {"latitude": -27.46, "longitude": -58.83},
                    "province": "Corrientes",
                    "total_detections": 15,
                    "avg_confidence": 87.5,
                    "is_significant": True,
                    "status": "extinguished"
                }],
                "pagination": {
                    "total": 1523,
                    "page": 1,
                    "page_size": 20,
                    "total_pages": 77,
                    "has_next": True,
                    "has_prev": False
                }
            }
        }


# =============================================================================
# DETAIL MODEL
# =============================================================================

class DetectionBrief(BaseModel):
    """Detección individual resumida."""
    id: UUID
    satellite: str
    detected_at: datetime
    latitude: float
    longitude: float
    frp: Optional[float] = None
    confidence: Optional[int] = None


class FireEventDetail(FireEventListItem):
    """
    Detalle completo de un evento de incendio.
    Extiende FireEventListItem con información adicional.
    """
    # Métricas adicionales
    avg_frp: Optional[float] = None
    sum_frp: Optional[float] = None
    
    # Procesamiento
    has_legal_analysis: bool = False
    processing_error: Optional[str] = None
    
    # Relaciones
    protected_areas: List[ProtectedAreaBrief] = []
    
    # Timestamps
    created_at: datetime
    updated_at: Optional[datetime] = None


class FireDetailResponse(BaseModel):
    """Response del detalle de incendio."""
    fire: FireEventDetail
    detections: List[DetectionBrief] = []
    related_fires_count: int = 0


# =============================================================================
# STATISTICS
# =============================================================================

class ProvinceStats(BaseModel):
    """Estadísticas por provincia."""
    name: str
    fire_count: int
    latest_fire: Optional[date] = None


class FireStatistics(BaseModel):
    """Estadísticas agregadas."""
    total_fires: int
    total_detections: int
    total_hectares: float
    avg_confidence: float
    fires_in_protected: int
    by_province: List[ProvinceStats]
    by_month: Dict[str, int]


class StatsResponse(BaseModel):
    """Response de estadísticas."""
    period: Dict[str, date]
    stats: FireStatistics
    generated_at: datetime = Field(default_factory=datetime.now)


# =============================================================================
# EXPORT
# =============================================================================

class ExportResult(BaseModel):
    """Resultado de exportación."""
    filename: str
    format: ExportFormat
    record_count: int
    file_size_bytes: int
    generated_at: datetime = Field(default_factory=datetime.now)