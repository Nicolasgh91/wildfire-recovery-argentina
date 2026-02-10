from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class RefreshResponse(BaseModel):
    fire_id: UUID = Field(..., description="Fire UUID")
    episode_id: Optional[UUID] = Field(None, description="Fire episode UUID")
    status: Literal["updated", "skipped", "not_found", "error"]
    reason: Optional[str] = Field(None, description="Reason when skipped or error")
    image_id: Optional[str] = Field(None, description="GEE system index used")
    slides_count: Optional[int] = Field(None, description="Number of slides generated")
