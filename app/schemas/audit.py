from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Dict, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class LandUseAuditRequest(BaseModel):
    """Request payload for land-use audits (UC-F06)."""

    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    radius_meters: Optional[int] = Field(default=None, ge=1)
    cadastral_id: Optional[str] = None


class AuditFire(BaseModel):
    fire_event_id: UUID
    fire_date: date
    distance_meters: float
    in_protected_area: bool
    prohibition_until: date
    years_remaining: int
    province: Optional[str] = None
    avg_confidence: Optional[float] = None
    estimated_area_hectares: Optional[float] = None
    protected_area_names: List[str] = Field(default_factory=list)
    protected_area_categories: List[str] = Field(default_factory=list)


class EvidenceThumbnail(BaseModel):
    fire_event_id: UUID
    thumbnail_url: str
    acquisition_date: Optional[date] = None
    image_type: Optional[str] = None
    gee_system_index: Optional[str] = None


class AuditEvidence(BaseModel):
    thumbnails: List[EvidenceThumbnail] = Field(default_factory=list)


class AuditResponse(BaseModel):
    audit_id: UUID
    audit_hash: str
    is_prohibited: bool
    prohibition_until: Optional[date]
    fires_found: int
    fires: List[AuditFire]
    evidence: AuditEvidence
    location: Dict[str, float]
    radius_meters: int
    cadastral_id: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# Audit search (historical episodes)
class AuditSearchBBox(BaseModel):
    minx: float
    miny: float
    maxx: float
    maxy: float


class AuditSearchResolvedPlace(BaseModel):
    label: str
    type: Literal["province", "protected_area", "address"]
    bbox: Optional[AuditSearchBBox] = None
    point: Optional[Dict[str, float]] = None


class AuditSearchEpisode(BaseModel):
    id: UUID
    start_date: datetime
    end_date: Optional[datetime] = None
    status: Optional[str] = None
    provinces: Optional[List[str]] = None
    estimated_area_hectares: Optional[float] = None
    detection_count: Optional[int] = None
    frp_max: Optional[float] = None


class AuditSearchDateRange(BaseModel):
    earliest: Optional[datetime] = None
    latest: Optional[datetime] = None


class AuditSearchResponse(BaseModel):
    resolved_place: AuditSearchResolvedPlace
    episodes: List[AuditSearchEpisode]
    total: int
    date_range: AuditSearchDateRange


# Backwards compatibility aliases
LandUseAuditResponse = AuditResponse
AuditRequest = LandUseAuditRequest
