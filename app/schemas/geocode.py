from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class GeocodeResult(BaseModel):
    lat: float
    lon: float
    display_name: str
    boundingbox: Optional[List[str]] = None
    source: str = Field(default="nominatim")


class GeocodeResponse(BaseModel):
    query: str
    result: GeocodeResult
