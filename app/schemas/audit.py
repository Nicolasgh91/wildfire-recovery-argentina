from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from uuid import UUID


class LandUseAuditRequest(BaseModel):
    """Request para auditoría de cambio de uso del suelo"""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    radius_meters: int = Field(500, ge=100, le=5000)
    cadastral_id: Optional[str] = None


class FireEvidenceItem(BaseModel):
    """Evidencia de un incendio individual"""
    fire_id: UUID
    fire_date: datetime
    frp: Optional[float]
    confidence: float
    protected_area: Optional[str]
    prohibition_until: date
    image_url: Optional[str]


class LandUseAuditResponse(BaseModel):
    """Respuesta de auditoría"""
    audit_id: UUID
    location: dict
    fires_found: int
    is_prohibited: bool
    prohibition_until: Optional[date]
    violation_severity: str
    
    fires: List[FireEvidenceItem]
    
    protected_areas_affected: List[str]
    
    summary: str
    legal_disclaimer: str