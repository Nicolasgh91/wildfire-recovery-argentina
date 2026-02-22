from __future__ import annotations

import hashlib
import json
import logging
from typing import Optional

import requests

from app.core.config import settings
from app.schemas.geocode import GeocodeResult

logger = logging.getLogger(__name__)

_CACHE_TTL = 86400  # 24 hours


class GeocodingService:
    """Service for forward geocoding via Nominatim."""
    def __init__(self):
        self.base_url = settings.GEOCODE_BASE_URL
        self.user_agent = settings.GEOCODE_USER_AGENT
        self.email = settings.GEOCODE_EMAIL
        self.country = settings.GEOCODE_COUNTRY
        self.timeout = settings.GEOCODE_TIMEOUT
        self.limit = settings.GEOCODE_LIMIT
        self._redis = None
        self._redis_available = False
        try:
            import redis as _redis_lib
            self._redis = _redis_lib.Redis.from_url(
                settings.REDIS_URL, decode_responses=True, socket_connect_timeout=2
            )
            self._redis.ping()
            self._redis_available = True
        except Exception as exc:
            logger.warning("Geocoding cache: Redis unavailable, running without cache: %s", exc)

    def _cache_key_fwd(self, query: str) -> str:
        h = hashlib.md5(query.lower().strip().encode()).hexdigest()
        return f"geocode:fwd:{h}"

    def _cache_key_rev(self, lat: float, lon: float) -> str:
        return f"geocode:rev:{lat:.5f}:{lon:.5f}"

    def _cache_get(self, key: str) -> Optional[dict]:
        if not self._redis_available:
            return None
        try:
            raw = self._redis.get(key)
            if raw:
                return json.loads(raw)
        except Exception as exc:
            logger.debug("geocoding cache get error: %s", exc)
        return None

    def _cache_set(self, key: str, data: dict) -> None:
        if not self._redis_available:
            return
        try:
            self._redis.setex(key, _CACHE_TTL, json.dumps(data))
        except Exception as exc:
            logger.debug("geocoding cache set error: %s", exc)

    @staticmethod
    def _result_from_cache(cached: dict) -> Optional[GeocodeResult]:
        try:
            return GeocodeResult(
                lat=cached["lat"],
                lon=cached["lon"],
                display_name=cached.get("display_name"),
                boundingbox=cached.get("boundingbox"),
            )
        except (KeyError, TypeError, ValueError):
            return None

    def geocode(self, query: str) -> Optional[GeocodeResult]:
        if not query:
            return None

        # BL-009: check cache first
        cache_key = self._cache_key_fwd(query)
        cached = self._cache_get(cache_key)
        if cached is not None:
            result = self._result_from_cache(cached)
            if result:
                return result

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

        result = GeocodeResult(
            lat=lat,
            lon=lon,
            display_name=display_name,
            boundingbox=boundingbox if isinstance(boundingbox, list) else None,
        )

        # BL-009: store in cache
        self._cache_set(cache_key, {
            "lat": lat, "lon": lon,
            "display_name": display_name,
            "boundingbox": boundingbox,
        })

        return result

    def reverse_geocode(self, lat: float, lon: float) -> Optional[GeocodeResult]:
        # BL-009: check cache first
        cache_key = self._cache_key_rev(lat, lon)
        cached = self._cache_get(cache_key)
        if cached is not None:
            result = self._result_from_cache(cached)
            if result:
                return result

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

        result = GeocodeResult(
            lat=resolved_lat,
            lon=resolved_lon,
            display_name=display_name,
            boundingbox=boundingbox if isinstance(boundingbox, list) else None,
        )

        # BL-009: store in cache
        self._cache_set(cache_key, {
            "lat": resolved_lat, "lon": resolved_lon,
            "display_name": display_name,
            "boundingbox": boundingbox,
        })

        return result
