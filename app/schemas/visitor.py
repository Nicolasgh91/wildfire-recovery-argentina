from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class CompanionInput(BaseModel):
    full_name: str = Field(..., min_length=2)
    age_range: Optional[str] = None
    document: Optional[str] = None


class VisitorLogCreate(BaseModel):
    shelter_id: UUID
    visit_date: date
    registration_type: str = Field(..., description="day_entry | overnight")
    group_leader_name: str
    group_leader_document: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    companions: List[CompanionInput] = Field(default_factory=list)


class VisitorLogUpdate(BaseModel):
    registration_type: Optional[str] = None
    group_leader_name: Optional[str] = None
    group_leader_document: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    companions: Optional[List[CompanionInput]] = None


class VisitorLogResponse(BaseModel):
    id: UUID
    shelter_id: UUID
    visit_date: date
    registration_type: str
    group_leader_name: str
    group_leader_document: Optional[str]
    contact_email: Optional[str]
    contact_phone: Optional[str]
    total_people: int
    companions: List[CompanionInput]
    created_at: datetime


class VisitorLogListResponse(BaseModel):
    total: int
    logs: List[VisitorLogResponse]


class ShelterResponse(BaseModel):
    id: UUID
    name: str
    province: str
    location_description: Optional[str] = None
    carrying_capacity: Optional[int] = None
    is_active: bool


class ShelterListResponse(BaseModel):
    total: int
    shelters: List[ShelterResponse]
