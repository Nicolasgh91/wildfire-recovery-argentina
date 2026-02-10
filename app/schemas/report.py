"""
Schemas Pydantic para Reportes - ForestGuard API.

Define los modelos de request/response para:
- UC-12: Reportes históricos de incendios
- UC-02: Peritajes judiciales (futuro)
- UC-09: Paquetes de evidencia (futuro)

Autor: ForestGuard Dev Team
Versión: 1.0.0
"""

from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# =============================================================================
# ENUMS
# =============================================================================


class ReportType(str, Enum):
    """Tipos de reportes disponibles."""

    HISTORICAL = "historical"
    JUDICIAL = "judicial"
    CITIZEN_EVIDENCE = "citizen_evidence"
    RECOVERY = "recovery"


class PostFireFrequency(str, Enum):
    """Frecuencia de imágenes post-incendio."""

    DAILY = "daily"
    MONTHLY = "monthly"
    ANNUAL = "annual"


class OutputFormat(str, Enum):
    """Formato de salida del reporte."""

    PDF = "pdf"
    WEB = "web"
    HYBRID = "hybrid"


class ReportStatus(str, Enum):
    """Estado del reporte."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class RecoveryStatusEnum(str, Enum):
    """Estados de recuperación de vegetación."""

    NOT_STARTED = "not_started"
    EARLY_RECOVERY = "early_recovery"
    MODERATE_RECOVERY = "moderate_recovery"
    ADVANCED_RECOVERY = "advanced_recovery"
    FULL_RECOVERY = "full_recovery"
    ANOMALY_DETECTED = "anomaly_detected"


# =============================================================================
# REQUEST SCHEMAS
# =============================================================================


class BoundingBox(BaseModel):
    """Bounding box geográfico."""

    west: float = Field(..., ge=-180, le=180, description="Longitud oeste")
    south: float = Field(..., ge=-90, le=90, description="Latitud sur")
    east: float = Field(..., ge=-180, le=180, description="Longitud este")
    north: float = Field(..., ge=-90, le=90, description="Latitud norte")

    @model_validator(mode="after")
    def validate_bbox(self):
        if self.west >= self.east:
            raise ValueError("west debe ser menor que east")
        if self.south >= self.north:
            raise ValueError("south debe ser menor que north")
        return self


class DateRange(BaseModel):
    """Rango de fechas para búsqueda."""

    start: date = Field(..., description="Fecha inicio")
    end: date = Field(..., description="Fecha fin")

    @model_validator(mode="after")
    def validate_range(self):
        if self.start > self.end:
            raise ValueError("start debe ser anterior o igual a end")
        return self


class ReportConfig(BaseModel):
    """Configuración de generación del reporte."""

    include_pre_fire: bool = Field(True, description="Incluir imagen pre-incendio")
    post_fire_frequency: PostFireFrequency = Field(
        PostFireFrequency.ANNUAL, description="Frecuencia de imágenes post-incendio"
    )
    max_images: int = Field(12, ge=1, le=20, description="Máximo de imágenes a incluir")
    vis_types: List[str] = Field(
        default=["RGB", "NDVI"],
        description="Tipos de visualización (RGB, NDVI, FALSE_COLOR)",
    )
    include_ndvi_chart: bool = Field(
        True, description="Incluir gráfico de evolución NDVI"
    )
    max_cloud_cover: float = Field(
        30.0, ge=0, le=100, description="Máximo % de nubes permitido"
    )


class HistoricalReportRequest(BaseModel):
    """
    Request para generar reporte histórico de incendios (UC-12).

    Ejemplo:
    ```json
    {
        "protected_area_id": "uuid-park-123",
        "fire_event_id": "uuid-fire-456",
        "fire_date": "2020-08-15",
        "bbox": {
            "west": -60.5,
            "south": -27.0,
            "east": -60.3,
            "north": -26.8
        },
        "report_config": {
            "post_fire_frequency": "annual",
            "max_images": 10
        }
    }
    ```
    """

    # Identificadores
    protected_area_id: Optional[str] = Field(None, description="ID del área protegida")
    protected_area_name: Optional[str] = Field(
        None, description="Nombre del área protegida"
    )
    fire_event_id: Optional[str] = Field(None, description="ID del evento de incendio")

    # Fecha del incendio (requerido)
    fire_date: date = Field(..., description="Fecha del incendio a analizar")

    # Área geográfica (requerido)
    bbox: BoundingBox = Field(..., description="Bounding box del área afectada")

    # Rango de análisis (opcional)
    date_range: Optional[DateRange] = Field(
        None, description="Rango de fechas para búsqueda (default: fire_date hasta hoy)"
    )

    # Configuración
    report_config: ReportConfig = Field(
        default_factory=ReportConfig, description="Configuración de generación"
    )

    # Output
    output_format: OutputFormat = Field(
        OutputFormat.HYBRID, description="Formato de salida"
    )

    # Solicitante
    requester_email: Optional[str] = Field(None, description="Email del solicitante")
    requester_name: Optional[str] = Field(None, description="Nombre del solicitante")

    @field_validator("fire_date")
    @classmethod
    def fire_date_not_future(cls, v):
        if v > date.today():
            raise ValueError("fire_date no puede ser una fecha futura")
        return v

    @model_validator(mode="after")
    def set_default_area_name(self):
        """Set default area name if not provided."""
        if self.protected_area_name is None:
            if self.protected_area_id:
                self.protected_area_name = f"Área {self.protected_area_id[:8]}"
            else:
                self.protected_area_name = "Área no especificada"
        return self

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "protected_area_name": "Parque Nacional Chaco",
                "fire_event_id": "550e8400-e29b-41d4-a716-446655440000",
                "fire_date": "2020-08-15",
                "bbox": {"west": -60.5, "south": -27.0, "east": -60.3, "north": -26.8},
                "report_config": {
                    "post_fire_frequency": "annual",
                    "max_images": 10,
                    "vis_types": ["RGB", "NDVI"],
                },
                "output_format": "hybrid",
            }
        }
    )


# =============================================================================
# RESPONSE SCHEMAS
# =============================================================================


class ImageEvidenceResponse(BaseModel):
    """Información de una imagen satelital en el reporte."""

    image_id: str = Field(..., description="ID único de la imagen")
    acquisition_date: date = Field(..., description="Fecha de adquisición")
    vis_type: str = Field(..., description="Tipo de visualización (RGB, NDVI)")
    thumbnail_url: str = Field(..., description="URL del thumbnail")
    hd_download_url: Optional[str] = Field(None, description="URL de descarga HD")
    cloud_cover_percent: float = Field(..., description="Porcentaje de nubes")
    satellite: str = Field("Sentinel-2", description="Satélite fuente")
    ndvi_mean: Optional[float] = Field(None, description="NDVI promedio del área")
    is_pre_fire: bool = Field(False, description="Indica si es imagen pre-incendio")


class RecoveryAnalysisResponse(BaseModel):
    """Resultado del análisis de recuperación."""

    analysis_date: date
    months_after_fire: int
    baseline_ndvi: float
    current_ndvi: float
    recovery_percentage: float = Field(..., ge=0, le=100)
    recovery_status: RecoveryStatusEnum
    anomaly_detected: bool
    anomaly_type: Optional[str] = None


class TemporalAnalysisResponse(BaseModel):
    """Análisis temporal completo."""

    fire_event_id: str
    protected_area_name: str
    fire_date: date
    analysis_period_start: date
    analysis_period_end: date

    # Baseline
    pre_fire_ndvi: float
    pre_fire_date: date

    # Serie
    post_fire_series: List[RecoveryAnalysisResponse]

    # Resumen
    total_images_analyzed: int
    images_with_anomalies: int
    final_recovery_status: RecoveryStatusEnum
    overall_recovery_percentage: float
    recovery_trend: str  # "improving", "stagnant", "declining"
    trend_confidence: float


class ReportOutputs(BaseModel):
    """URLs de salida del reporte."""

    pdf_url: Optional[str] = Field(None, description="URL del PDF generado")
    web_viewer_url: Optional[str] = Field(
        None, description="URL del visor web interactivo"
    )
    images: List[ImageEvidenceResponse] = Field(default_factory=list)


class ReportMetadata(BaseModel):
    """Metadata del reporte generado."""

    protected_area: Optional[str] = None
    fire_date: Optional[date] = None
    total_affected_hectares: float = 0
    verification_hash: str = Field(..., description="Hash SHA-256 del contenido")
    data_sources: List[str] = Field(
        default=["Sentinel-2 L2A (ESA)", "NASA FIRMS"],
        description="Fuentes de datos utilizadas",
    )


class HistoricalReportResponse(BaseModel):
    """
    Response de generación de reporte histórico (UC-12).

    Ejemplo de respuesta exitosa:
    ```json
    {
        "report_id": "RPT-HIST-20250129-A1B2C3",
        "status": "completed",
        "fire_events_found": 1,
        "outputs": {
            "pdf_url": "https://storage.googleapis.com/forestguard-reports/reports/historical/RPT-HIST-20250129-A1B2C3.pdf",
            "web_viewer_url": "https://forestguard.../viewer/RPT-HIST-20250129-A1B2C3",
            "images": [...]
        },
        "analysis": {...},
        "metadata": {
            "verification_hash": "sha256:a3f5b8c9..."
        }
    }
    ```
    """

    report_id: str = Field(..., description="ID único del reporte")
    report_type: ReportType = Field(ReportType.HISTORICAL)
    status: ReportStatus = Field(..., description="Estado del reporte")

    # Resultados
    fire_events_found: int = Field(0, description="Número de eventos encontrados")
    images_collected: int = Field(0, description="Imágenes recolectadas")

    # Outputs
    outputs: ReportOutputs = Field(default_factory=ReportOutputs)

    # Análisis (opcional, si se completó)
    analysis: Optional[TemporalAnalysisResponse] = None

    # Metadata y verificación
    metadata: Optional[ReportMetadata] = None
    verification_url: Optional[str] = Field(
        None, description="URL para verificar autenticidad"
    )

    # Timestamps
    requested_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    # Errores
    error_message: Optional[str] = Field(None, description="Mensaje de error si falló")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "report_id": "RPT-HIST-20250129-A1B2C3",
                "report_type": "historical",
                "status": "completed",
                "fire_events_found": 1,
                "images_collected": 8,
                "outputs": {
                    "pdf_url": "https://storage.googleapis.com/forestguard-reports/reports/historical/RPT-HIST-20250129-A1B2C3.pdf",
                    "web_viewer_url": "https://forestguard.freedynamicdns.org/viewer/RPT-HIST-20250129-A1B2C3",
                    "images": [
                        {
                            "image_id": "S2A_20200801",
                            "acquisition_date": "2020-08-01",
                            "vis_type": "RGB",
                            "thumbnail_url": "https://storage.googleapis.com/forestguard-images/thumbnails/...",
                            "cloud_cover_percent": 5.2,
                            "is_pre_fire": True,
                        }
                    ],
                },
                "metadata": {
                    "protected_area": "Parque Nacional Chaco",
                    "verification_hash": "sha256:a3f5b8c9d2e1f0...",
                },
                "verification_url": "https://forestguard.freedynamicdns.org/verify/RPT-HIST-20250129-A1B2C3",
            }
        }
    )


# =============================================================================
# SCHEMAS ADICIONALES
# =============================================================================


class ReportVerificationRequest(BaseModel):
    """Request para verificar autenticidad de un reporte."""

    report_id: str = Field(..., description="ID del reporte a verificar")
    expected_hash: Optional[str] = Field(None, description="Hash esperado (opcional)")


class ReportVerificationResponse(BaseModel):
    """Response de verificación de reporte."""

    report_id: str
    is_valid: bool
    expected_hash: Optional[str] = None
    actual_hash: Optional[str] = None
    verified_at: datetime
    error: Optional[str] = None


class ReportListItem(BaseModel):
    """Item en lista de reportes."""

    report_id: str
    report_type: ReportType
    status: ReportStatus
    protected_area_name: Optional[str]
    fire_date: Optional[date]
    created_at: datetime
    pdf_url: Optional[str]


class ReportListResponse(BaseModel):
    """Response de listado de reportes."""

    total: int
    page: int
    per_page: int
    reports: List[ReportListItem]
