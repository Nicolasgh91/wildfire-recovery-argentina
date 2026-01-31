from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ClimateSnapshot(BaseModel):
    temperature_c: Optional[float] = Field(None, description="Air temperature in Celsius")
    wind_speed_kmh: Optional[float] = Field(None, description="Wind speed in km/h")
    humidity_pct: Optional[float] = Field(None, ge=0, le=100, description="Relative humidity")
    drought_index: Optional[float] = Field(None, ge=0, le=5, description="Drought severity (0-5)")


class ParkCapacityAlertRequest(BaseModel):
    protected_area_id: UUID = Field(..., description="Protected area UUID")
    alert_date: date = Field(..., description="Date of the alert")
    visitor_count: int = Field(..., ge=0, description="Reported visitor count")
    carrying_capacity: Optional[int] = Field(None, ge=1, description="Override carrying capacity")
    climate: Optional[ClimateSnapshot] = None


class ParkCapacityAlertResponse(BaseModel):
    alert_id: UUID
    protected_area_id: UUID
    alert_date: date
    visitor_count: int
    carrying_capacity: int
    occupancy_pct: float
    risk_score: float
    risk_level: str
    alert_level: str
    recommended_action: str
    created_at: datetime
