from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ExplorationStatus(str, Enum):
    draft = "draft"
    quoted = "quoted"
    processing = "processing"
    ready = "ready"
    failed = "failed"


class ExplorationItemStatus(str, Enum):
    pending = "pending"
    queued = "queued"
    generated = "generated"
    failed = "failed"


class ExplorationItemKind(str, Enum):
    pre = "pre"
    post = "post"


class ExplorationCreateRequest(BaseModel):
    fire_event_id: UUID
    title: Optional[str] = Field(None, max_length=200)


class ExplorationUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, max_length=200)


class ExplorationItemCreateRequest(BaseModel):
    kind: ExplorationItemKind
    target_date: datetime
    sensor: Optional[str] = Field(None, max_length=50)
    aoi: Optional[Dict[str, Any]] = None
    geometry_ref: Optional[str] = None
    visualization_params: Optional[Dict[str, Any]] = None


class ExplorationItemResponse(BaseModel):
    id: UUID
    kind: ExplorationItemKind
    target_date: datetime
    sensor: Optional[str] = None
    aoi: Optional[Dict[str, Any]] = None
    geometry_ref: Optional[str] = None
    visualization_params: Optional[Dict[str, Any]] = None
    status: ExplorationItemStatus
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExplorationResponse(BaseModel):
    id: UUID
    fire_event_id: Optional[UUID] = None
    title: Optional[str] = None
    status: ExplorationStatus
    created_at: datetime
    updated_at: datetime
    items: List[ExplorationItemResponse] = []

    model_config = ConfigDict(from_attributes=True)


class ExplorationListItem(BaseModel):
    id: UUID
    fire_event_id: Optional[UUID] = None
    title: Optional[str] = None
    status: ExplorationStatus
    created_at: datetime
    updated_at: datetime
    items_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class PaginationMeta(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool

    @classmethod
    def create(cls, total: int, page: int, page_size: int) -> "PaginationMeta":
        if page_size < 1:
            page_size = 20
        total_pages = (total + page_size - 1) // page_size
        return cls(
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        )


class ExplorationListResponse(BaseModel):
    investigations: List[ExplorationListItem]
    pagination: PaginationMeta


class ExplorationQuoteResponse(BaseModel):
    items_count: int
    unit_price_ars: int
    total_price_ars: int
    credits_required: int
    suggestions: List[str] = []


class ExplorationGenerateResponse(BaseModel):
    job_id: UUID
    status: str
    items_count: int
    credits_spent: int
    credits_remaining: int


class ExplorationAssetResponse(BaseModel):
    id: UUID
    item_id: UUID
    signed_url: str
    mime: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    sha256: Optional[str] = None
    generated_at: Optional[datetime] = None
    target_date: datetime
    kind: ExplorationItemKind
    status: ExplorationItemStatus

    model_config = ConfigDict(from_attributes=True)


class ExplorationAssetsResponse(BaseModel):
    assets: List[ExplorationAssetResponse]
