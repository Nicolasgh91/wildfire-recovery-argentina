"""
Modelos de datos usando Pydantic
Define la estructura de requests/responses de la API
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import date, datetime
from enum import Enum


# ========== ENUMS ==========

class TipoIncendio(str, Enum):
    """Tipos de incendio"""
    NUEVO = "nuevo"
    RECURRENTE = "recurrente"


class EstadoAnalisis(str, Enum):
    """Estados del análisis"""
    PENDIENTE = "pendiente"
    PROCESANDO = "procesando"
    COMPLETADO = "completado"
    ERROR = "error"


class CalidadImagen(str, Enum):
    """Calidad de imagen satelital"""
    EXCELENTE = "excelente"
    BUENA = "buena"
    REGULAR = "regular"
    MALA = "mala"


# ========== REQUEST MODELS ==========

class DetectarIncendiosRequest(BaseModel):
    """Request para detectar incendios en una región"""
    provincia: str = Field(..., description="Nombre de la provincia")
    fecha_inicio: date = Field(..., description="Fecha inicio búsqueda")
    fecha_fin: date = Field(..., description="Fecha fin búsqueda")
    umbral_confianza: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Umbral de confianza (0-1)"
    )
    
    @validator('fecha_fin')
    def fecha_fin_mayor_inicio(cls, v, values):
        """Valida que fecha_fin > fecha_inicio"""
        if 'fecha_inicio' in values and v < values['fecha_inicio']:
            raise ValueError('fecha_fin debe ser mayor a fecha_inicio')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "provincia": "Buenos Aires",
                "fecha_inicio": "2023-01-01",
                "fecha_fin": "2023-12-31",
                "umbral_confianza": 0.8
            }
        }


class CrearIncendioRequest(BaseModel):
    """Request para crear un incendio manualmente"""
    fecha_deteccion: date
    provincia: str
    localidad: Optional[str] = None
    latitud: float = Field(..., ge=-90, le=90)
    longitud: float = Field(..., ge=-180, le=180)
    area_afectada_hectareas: Optional[float] = Field(None, ge=0)
    
    class Config:
        json_schema_extra = {
            "example": {
                "fecha_deteccion": "2023-06-15",
                "provincia": "Córdoba",
                "localidad": "Villa Carlos Paz",
                "latitud": -31.4135,
                "longitud": -64.4955,
                "area_afectada_hectareas": 150.5
            }
        }


class IniciarAnalisisRequest(BaseModel):
    """Request para iniciar análisis de un incendio"""
    incendio_id: str = Field(..., description="UUID del incendio")
    forzar: bool = Field(
        default=False,
        description="Forzar reanalisis si ya existe"
    )


# ========== RESPONSE MODELS ==========

class IncendioResponse(BaseModel):
    """Response con datos de un incendio"""
    id: str
    fecha_deteccion: date
    provincia: str
    localidad: Optional[str]
    latitud: float
    longitud: float
    area_afectada_hectareas: Optional[float]
    tipo: TipoIncendio
    incendio_previo_id: Optional[str]
    estado_analisis: EstadoAnalisis
    error_mensaje: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class AnalisisMensualResponse(BaseModel):
    """Response con análisis mensual"""
    id: str
    incendio_id: str
    mes_numero: int = Field(..., ge=1, le=36)
    fecha_imagen: date
    ndvi_promedio: Optional[float]
    ndvi_min: Optional[float]
    ndvi_max: Optional[float]
    ndvi_desviacion: Optional[float]
    construcciones_detectadas: bool
    porcentaje_recuperacion: Optional[float]
    calidad_imagen: Optional[CalidadImagen]
    nubosidad_porcentaje: Optional[float]
    notas: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class SuperposicionResponse(BaseModel):
    """Response con datos de superposición"""
    id: str
    incendio_a_id: str
    incendio_b_id: str
    porcentaje_superposicion: float
    area_superpuesta_hectareas: Optional[float]
    dias_transcurridos: Optional[int]
    created_at: datetime
    
    class Config:
        from_attributes = True


class IncendioDetalleResponse(BaseModel):
    """Response detallado de un incendio con análisis y superposiciones"""
    incendio: IncendioResponse
    analisis_mensual: List[AnalisisMensualResponse] = []
    superposiciones: List[SuperposicionResponse] = []
    
    @property
    def progreso_analisis(self) -> float:
        """Calcula el progreso del análisis (0-100%)"""
        if not self.analisis_mensual:
            return 0.0
        return round((len(self.analisis_mensual) / 36) * 100, 2)


class EstadisticasResponse(BaseModel):
    """Response con estadísticas generales"""
    total_incendios: int
    incendios_recurrentes: int
    analisis_completados: int
    porcentaje_completado: float


class HealthCheckResponse(BaseModel):
    """Response del health check"""
    status: str
    timestamp: datetime
    services: dict
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": "2024-01-21T10:30:00",
                "services": {
                    "database": "ok",
                    "gee": "ok"
                }
            }
        }


# ========== UTILITY MODELS ==========

class ErrorResponse(BaseModel):
    """Response estándar para errores"""
    detail: str
    error_code: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_schema_extra = {
            "example": {
                "detail": "Incendio no encontrado",
                "error_code": "INCENDIO_NOT_FOUND",
                "timestamp": "2024-01-21T10:30:00"
            }
        }


class PaginatedResponse(BaseModel):
    """Response paginada genérica"""
    items: List
    total: int
    page: int
    page_size: int
    total_pages: int
    
    @property
    def has_next(self) -> bool:
        return self.page < self.total_pages
    
    @property
    def has_prev(self) -> bool:
        return self.page > 1