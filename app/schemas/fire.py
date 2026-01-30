from datetime import date, datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from uuid import UUID
import math

from pydantic import BaseModel, Field, ConfigDict, computed_field

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
# SHARED MODELS
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


# =============================================================================
# LIST ITEMS & RESPONSES
# =============================================================================

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
    
    # Ubicación (Centroid ahora es Coordinates object en el output, pero en DB es geo shape.
    # Necesitaremos procesarlo o usar validator, por ahora asumimos el field simple)
    # Sin embargo, app/models/fire.py usa geoalchemy, así que centroid no es trivial.
    # Mantendremos simple por ahora, adaptando en route.
    # centroid: Coordinates 
    # Para simplificar integración inicial, usaremos lat/lon sueltos si es posible, o adaptamos a un dict.
    
    # Adaptación: Definimos lat/lon aquí para facilitar serialización desde el modelo
    # El modelo tiene centroid como WKBElement. Lo convertiremos en el crud/route.
    # O usamos un schema que acepte dict.
    
    centroid: Optional[Dict[str, float]] = None # {"latitude": x, "longitude": y}
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
        """Calcula estado basado en temporalidad (Lógica simple por ahora)."""
        now = datetime.now()
        # Si end_date es muy reciente o futuro, es activo?
        # En datos históricos, end_date es el final.
        days_since_end = (now.replace(tzinfo=None) - self.end_date.replace(tzinfo=None)).days
        
        if days_since_end < 0: return FireStatus.ACTIVE
        if days_since_end < 3: return FireStatus.CONTROLLED
        if days_since_end < 14: return FireStatus.MONITORING
        return FireStatus.EXTINGUISHED

    model_config = ConfigDict(from_attributes=True)


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
        if page_size < 1: page_size = 20
        total_pages = math.ceil(total / page_size)
        return cls(
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1
        )


class FireListResponse(BaseModel):
    """Response del listado de incendios (UC-13)."""
    fires: List[FireEventListItem]
    pagination: PaginationMeta
    filters_applied: Dict[str, Any] = {}
    generated_at: datetime = Field(default_factory=datetime.now)


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
    
    model_config = ConfigDict(from_attributes=True)


class FireEventDetail(FireEventListItem):
    """Detalle completo de un evento de incendio."""
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
    name: str
    fire_count: int
    latest_fire: Optional[date] = None

class FireStatistics(BaseModel):
    total_fires: int
    total_detections: int
    total_hectares: float
    avg_confidence: float
    fires_in_protected: int
    by_province: List[ProvinceStats]
    by_month: Dict[str, int]

class StatsResponse(BaseModel):
    period: Dict[str, date]
    stats: FireStatistics
    generated_at: datetime = Field(default_factory=datetime.now)


# =============================================================================
# LEGACY / COMPATIBILITY
# =============================================================================
# Mantenemos estos por si acaso algún otro módulo los importaba,
# pero idealmente deberíamos refactorizar para usar FireEventListItem
class FireEventBase(BaseModel):
    start_date: datetime
    end_date: datetime
    total_detections: int
    max_frp: Optional[float]
    avg_confidence: Optional[float]
    estimated_area_hectares: Optional[float]
    province: Optional[str] = "Por determinar"
    is_significant: bool

class FireEventRead(FireEventBase):
    id: UUID
    model_config = ConfigDict(from_attributes=True)
