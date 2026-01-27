from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime, date
from typing import Optional, List
from uuid import UUID

# --- Schemas para Detecciones (Puntos) ---
class FireDetectionBase(BaseModel):
    satellite: str
    detected_at: datetime
    latitude: float
    longitude: float
    confidence: int = Field(alias="confidence_normalized")
    frp: Optional[float] = Field(alias="fire_radiative_power")

class FireDetectionRead(FireDetectionBase):
    id: UUID
    # Configuración nueva de Pydantic v2 para leer de ORM
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# --- Schemas para Eventos (Incendios Agrupados) ---
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
    # detections: List[FireDetectionRead] = [] # Opcional si quisieras anidar

    model_config = ConfigDict(from_attributes=True)