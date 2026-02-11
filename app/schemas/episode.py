from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class EpisodeBBox(BaseModel):
    minx: float
    miny: float
    maxx: float
    maxy: float


class EpisodeSlideItem(BaseModel):
    type: str
    thumbnail_url: Optional[str] = None
    url: Optional[str] = None
    satellite_image_id: Optional[str] = None
    generated_at: Optional[str] = None


class FireEpisodeListItem(BaseModel):
    id: UUID
    status: str
    start_date: datetime
    end_date: Optional[datetime] = None
    last_seen_at: Optional[datetime] = None
    bbox: Optional[EpisodeBBox] = None
    centroid_lat: Optional[float] = None
    centroid_lon: Optional[float] = None
    provinces: Optional[List[str]] = None
    event_count: int
    detection_count: int
    frp_sum: Optional[float] = None
    frp_max: Optional[float] = None
    estimated_area_hectares: Optional[float] = None
    gee_candidate: bool = False
    gee_priority: Optional[int] = None
    slides_data: Optional[List[EpisodeSlideItem]] = None
    representative_event_id: Optional[UUID] = None

    model_config = ConfigDict(from_attributes=True)


class FireEpisodeEventItem(BaseModel):
    id: UUID
    start_date: datetime
    end_date: datetime
    province: Optional[str] = None
    total_detections: Optional[int] = None
    max_frp: Optional[float] = None
    estimated_area_hectares: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class FireEpisodeDetail(FireEpisodeListItem):
    events: List[FireEpisodeEventItem] = []


class FireEpisodeListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int
    episodes: List[FireEpisodeListItem]
