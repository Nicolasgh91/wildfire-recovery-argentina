from __future__ import annotations

from datetime import date, datetime
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class RecurrenceCell(BaseModel):
    h3: str
    intensity: float = Field(..., ge=0, le=1)
    recurrence_class: Optional[str] = None
    total_fires: Optional[int] = None


class RecurrenceResponse(BaseModel):
    cells: List[RecurrenceCell]
    cell_count: int
    max_intensity: float
    bbox: Dict[str, float]
    generated_at: datetime = Field(default_factory=datetime.now)


class TrendPoint(BaseModel):
    period: date
    fire_count: int
    total_hectares: float


class TrendProjection(BaseModel):
    period: date
    projected_fire_count: float
    projected_total_hectares: float
    confidence_interval_low: float
    confidence_interval_high: float


class TrendsResponse(BaseModel):
    granularity: Literal["day", "month"]
    period: Dict[str, date]
    bbox: Optional[Dict[str, float]] = None
    series: List[TrendPoint]
    trend_direction: str
    period_change_rate_pct: float
    annual_change_rate_pct: float
    projections: Optional[List[TrendProjection]] = None
    total_fires: int
    total_hectares: float
    generated_at: datetime = Field(default_factory=datetime.now)
