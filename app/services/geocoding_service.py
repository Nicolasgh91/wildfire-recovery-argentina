from __future__ import annotations

import logging
from typing import Optional

import requests

from app.core.config import settings
from app.schemas.geocode import GeocodeResult

logger = logging.getLogger(__name__)


class GeocodingService:
    """Service for forward geocoding via Nominatim."""
    def __init__(self):
        self.base_url = settings.GEOCODE_BASE_URL
        self.user_agent = settings.GEOCODE_USER_AGENT
        self.email = settings.GEOCODE_EMAIL
        self.country = settings.GEOCODE_COUNTRY
        self.timeout = settings.GEOCODE_TIMEOUT
        self.limit = settings.GEOCODE_LIMIT

    def geocode(self, query: str) -> Optional[GeocodeResult]:
        if not query:
            return None

        params = {
            "q": query,
            "format": "jsonv2",
            "limit": self.limit,
        }

        if self.country:
            params["countrycodes"] = self.country
        if self.email:
            params["email"] = self.email

        headers = {"User-Agent": self.user_agent}

        try:
            response = requests.get(
                self.base_url, params=params, headers=headers, timeout=self.timeout
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.warning("geocoding request failed: %s", exc)
            return None

        try:
            data = response.json()
        except ValueError:
            logger.warning("geocoding response is not valid json")
            return None

        if not isinstance(data, list) or not data:
            return None

        item = data[0]
        try:
            lat = float(item.get("lat"))
            lon = float(item.get("lon"))
        except (TypeError, ValueError):
            return None

        display_name = item.get("display_name") or query
        boundingbox = item.get("boundingbox")

        return GeocodeResult(
            lat=lat,
            lon=lon,
            display_name=display_name,
            boundingbox=boundingbox if isinstance(boundingbox, list) else None,
        )

    def reverse_geocode(self, lat: float, lon: float) -> Optional[GeocodeResult]:
        reverse_url = (
            self.base_url.replace("/search", "/reverse")
            if "/search" in self.base_url
            else f"{self.base_url.rstrip('/')}/reverse"
        )

        params = {
            "lat": lat,
            "lon": lon,
            "format": "jsonv2",
        }

        if self.country:
            params["countrycodes"] = self.country
        if self.email:
            params["email"] = self.email

        headers = {"User-Agent": self.user_agent}

        try:
            response = requests.get(
                reverse_url, params=params, headers=headers, timeout=self.timeout
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.warning("reverse geocoding request failed: %s", exc)
            return None

        try:
            data = response.json()
        except ValueError:
            logger.warning("reverse geocoding response is not valid json")
            return None

        if not isinstance(data, dict):
            return None

        try:
            resolved_lat = float(data.get("lat"))
            resolved_lon = float(data.get("lon"))
        except (TypeError, ValueError):
            return None

        display_name = data.get("display_name") or f"{lat}, {lon}"
        boundingbox = data.get("boundingbox")

        return GeocodeResult(
            lat=resolved_lat,
            lon=resolved_lon,
            display_name=display_name,
            boundingbox=boundingbox if isinstance(boundingbox, list) else None,
        )
