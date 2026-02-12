import math
from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

# =============================================================================
# ENUMS
# =============================================================================


class FireStatus(str, Enum):
    """Estados de un evento de incendio."""

    ACTIVE = "active"
    CONTROLLED = "controlled"
    EXTINGUISHED = "extinguished"
    MONITORING = "monitoring"


class StatusScope(str, Enum):
    """Filtro rapido de estado (activo/historico/todos)."""

    ACTIVE = "active"
    HISTORICAL = "historical"
    ALL = "all"


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


class SlideItem(BaseModel):
    """Item de carrusel satelital."""

    type: str
    title: str
    url: str
    description: Optional[str] = None
    date: Optional[str] = None


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

    centroid: Optional[Dict[str, float]] = None  # {"latitude": x, "longitude": y}
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
    overlap_percentage: Optional[float] = None
    count_protected_areas: Optional[int] = None

    status: Optional[FireStatus] = None
    slides_data: Optional[List[SlideItem]] = None

    @model_validator(mode="after")
    def _ensure_status(self):
        if self.status is not None:
            return self

        if not self.end_date:
            self.status = FireStatus.EXTINGUISHED
            return self

        now = datetime.now()
        days_since_end = (
            now.replace(tzinfo=None) - self.end_date.replace(tzinfo=None)
        ).days

        if days_since_end < 0:
            self.status = FireStatus.ACTIVE
        elif days_since_end < 3:
            self.status = FireStatus.CONTROLLED
        elif days_since_end < 14:
            self.status = FireStatus.MONITORING
        else:
            self.status = FireStatus.EXTINGUISHED

        return self

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
        if page_size < 1:
            page_size = 20
        total_pages = math.ceil(total / page_size)
        return cls(
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        )


class FireListResponse(BaseModel):
    """Response del listado de incendios (UC-13)."""

    fires: List[FireEventListItem]
    pagination: PaginationMeta
    filters_applied: Dict[str, Any] = {}
    generated_at: datetime = Field(default_factory=datetime.now)


class FireSearchItem(BaseModel):
    """Item resumido para bÃºsqueda humana en exploraciÃ³n."""

    id: UUID
    start_date: datetime
    end_date: datetime
    province: Optional[str] = None
    department: Optional[str] = None
    estimated_area_hectares: Optional[float] = None
    avg_confidence: Optional[float] = Field(None, ge=0, le=100)
    quality_score: Optional[float] = Field(None, ge=0, le=100)
    total_detections: int = 0
    has_satellite_imagery: bool = False
    centroid: Optional[Dict[str, float]] = None
    status: Optional[FireStatus] = None

    model_config = ConfigDict(from_attributes=True)


class FireSearchResponse(BaseModel):
    """Response para bÃºsqueda de incendios en exploraciÃ³n."""

    fires: List[FireSearchItem]
    pagination: PaginationMeta
    filters_applied: Dict[str, Any] = {}
    generated_at: datetime = Field(default_factory=datetime.now)


class ExplorationPreviewTimeline(BaseModel):
    """Timeline sugerida para explorar un incendio."""

    before: List[date] = []
    during: List[date] = []
    after: List[date] = []


class ExplorationPreviewResponse(BaseModel):
    """Response para preview informativo sin GEE."""

    fire_event_id: UUID
    province: Optional[str] = None
    department: Optional[str] = None
    start_date: datetime
    end_date: datetime
    extinguished_at: Optional[datetime] = None
    centroid: Optional[Dict[str, float]] = None
    bbox: Optional[Dict[str, float]] = None
    perimeter_geojson: Optional[Dict[str, Any]] = None
    estimated_area_hectares: Optional[float] = None
    duration_days: Optional[int] = None
    has_satellite_imagery: bool = False
    timeline: ExplorationPreviewTimeline

    model_config = ConfigDict(from_attributes=True)


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

    source_type: Literal["event", "episode"] = "event"
    episode_id: Optional[UUID] = None
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


class TopFrpFire(BaseModel):
    id: UUID
    max_frp: Optional[float] = None
    province: Optional[str] = None
    start_date: Optional[datetime] = None


class FireStatistics(BaseModel):
    total_fires: int
    active_fires: int = 0
    historical_fires: int = 0
    total_detections: int
    total_hectares: float
    avg_hectares: float = 0
    median_hectares: float = 0
    avg_confidence: float
    fires_in_protected: int
    protected_percentage: float = 0
    significant_fires: int = 0
    significant_percentage: float = 0
    top_frp_fires: List[TopFrpFire] = []
    by_province: List[ProvinceStats]
    by_month: Dict[str, int]


class MetricComparison(BaseModel):
    current: float
    previous: float
    delta: float
    delta_pct: Optional[float] = None


class YtdComparison(BaseModel):
    total_fires: MetricComparison
    total_hectares: MetricComparison
    total_detections: MetricComparison
    avg_confidence: MetricComparison
    significant_fires: MetricComparison


class StatsResponse(BaseModel):
    """Estadísticas de incendios para un período."""

    period: Dict[str, date]
    stats: FireStatistics
    ytd_comparison: Optional[YtdComparison] = None
    generated_at: datetime = Field(default_factory=datetime.now)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "period": {"from": "2026-01-01", "to": "2026-01-31"},
                "stats": {
                    "total_fires": 234,
                    "active_fires": 12,
                    "historical_fires": 222,
                    "total_detections": 15678,
                    "total_hectares": 45230.5,
                    "avg_hectares": 193.3,
                    "avg_confidence": 82.4,
                    "fires_in_protected": 45,
                    "protected_percentage": 19.2,
                    "significant_fires": 28,
                    "by_province": [
                        {
                            "name": "Córdoba",
                            "fire_count": 67,
                            "latest_fire": "2026-01-30",
                        }
                    ],
                    "by_month": {"2026-01": 234},
                },
                "generated_at": "2026-02-08T12:00:00Z",
            }
        }
    )


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


# =============================================================================
# SAVED FILTERS (UC-F03)
# =============================================================================


class SavedFilterBase(BaseModel):
    filter_name: str = Field(..., max_length=100)
    filter_config: Dict[str, Any] = Field(default_factory=dict)
    is_default: bool = False


class SavedFilterCreate(SavedFilterBase):
    pass


class SavedFilterResponse(SavedFilterBase):
    id: UUID
    created_at: datetime
    last_used_at: Optional[datetime] = None
    use_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class SavedFilterListResponse(BaseModel):
    filters: List[SavedFilterResponse]


class ExportRequestStatus(BaseModel):
    status: str
    message: str
    job_id: Optional[str] = None
    total_records: Optional[int] = None
