from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class QualityClass(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class SeverityLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class QualityLimitation(BaseModel):
    code: str
    description: str
    severity: SeverityLevel = SeverityLevel.LOW


class QualitySource(BaseModel):
    source_name: str
    source_type: Optional[str] = None
    spatial_resolution_meters: Optional[int] = None
    temporal_resolution_hours: Optional[int] = None
    coverage_area: Optional[str] = None
    typical_accuracy_percentage: Optional[float] = None
    known_limitations: Optional[str] = None
    is_admissible_in_court: Optional[bool] = None
    legal_precedent_cases: Optional[List[str]] = None
    data_provider: Optional[str] = None
    provider_url: Optional[str] = None
    documentation_url: Optional[str] = None
    last_updated: Optional[datetime] = None
    is_used: Optional[bool] = None

    model_config = ConfigDict(from_attributes=True)


class QualityMetrics(BaseModel):
    reliability_score: float = Field(..., ge=0, le=100)
    classification: QualityClass
    confidence_score: float = Field(..., ge=0, le=100)
    imagery_score: float = Field(..., ge=0, le=100)
    climate_score: float = Field(..., ge=0, le=100)
    independent_score: float = Field(..., ge=0, le=100)
    avg_confidence: float = Field(..., ge=0, le=100)
    total_detections: int = Field(..., ge=0)
    independent_sources: int = Field(..., ge=0)
    has_imagery: bool
    has_climate: bool
    has_ndvi: bool
    score_calculated_at: datetime


class QualityResponse(BaseModel):
    fire_event_id: UUID
    start_date: datetime
    province: Optional[str] = None
    metrics: QualityMetrics
    limitations: List[QualityLimitation] = Field(default_factory=list)
    sources: List[QualitySource] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
