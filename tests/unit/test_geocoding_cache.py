"""Tests for geocoding Redis cache (BL-009 / PERF-003)."""
import json
from unittest.mock import MagicMock, patch

import fakeredis
import pytest

from app.schemas.geocode import GeocodeResult


class TestGeocodingCache:
    """Test cache hit, miss+store, and graceful fallback."""

    def _make_service(self, redis_client=None):
        """Create GeocodingService with injected Redis client."""
        with patch("app.services.geocoding_service.settings") as mock_s:
            mock_s.GEOCODE_BASE_URL = "https://nominatim.openstreetmap.org/search"
            mock_s.GEOCODE_USER_AGENT = "test/1.0"
            mock_s.GEOCODE_EMAIL = None
            mock_s.GEOCODE_COUNTRY = "ar"
            mock_s.GEOCODE_TIMEOUT = 5
            mock_s.GEOCODE_LIMIT = 1
            mock_s.REDIS_URL = "redis://localhost:6379/0"

            # Prevent real Redis connection in __init__
            with patch("app.services.geocoding_service.GeocodingService.__init__", lambda self: None):
                from app.services.geocoding_service import GeocodingService
                svc = GeocodingService()
                svc.base_url = mock_s.GEOCODE_BASE_URL
                svc.user_agent = mock_s.GEOCODE_USER_AGENT
                svc.email = mock_s.GEOCODE_EMAIL
                svc.country = mock_s.GEOCODE_COUNTRY
                svc.timeout = mock_s.GEOCODE_TIMEOUT
                svc.limit = mock_s.GEOCODE_LIMIT
                svc._redis = redis_client
                svc._redis_available = redis_client is not None
                return svc

    def test_cache_hit_no_http(self):
        """Second identical query should come from cache, no HTTP call."""
        redis_client = fakeredis.FakeRedis(decode_responses=True)
        svc = self._make_service(redis_client)

        # Pre-populate cache
        key = svc._cache_key_fwd("cordoba argentina")
        redis_client.setex(key, 86400, json.dumps({
            "lat": -31.4201, "lon": -64.1888,
            "display_name": "Córdoba, Argentina",
            "boundingbox": None,
        }))

        # Should return from cache without any HTTP call
        with patch("app.services.geocoding_service.requests.get") as mock_get:
            result = svc.geocode("cordoba argentina")
            mock_get.assert_not_called()

        assert result is not None
        assert result.lat == pytest.approx(-31.4201)
        assert result.lon == pytest.approx(-64.1888)

    def test_cache_miss_stores_result(self):
        """On cache miss, HTTP is called and result is stored in Redis."""
        redis_client = fakeredis.FakeRedis(decode_responses=True)
        svc = self._make_service(redis_client)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"lat": "-34.6037", "lon": "-58.3816", "display_name": "Buenos Aires", "boundingbox": None}
        ]

        with patch("app.services.geocoding_service.requests.get", return_value=mock_response):
            result = svc.geocode("buenos aires")

        assert result is not None
        assert result.lat == pytest.approx(-34.6037)

        # Verify it was cached
        key = svc._cache_key_fwd("buenos aires")
        cached = redis_client.get(key)
        assert cached is not None
        data = json.loads(cached)
        assert data["lat"] == -34.6037

    def test_reverse_cache_hit(self):
        """Reverse geocode cache hit."""
        redis_client = fakeredis.FakeRedis(decode_responses=True)
        svc = self._make_service(redis_client)

        key = svc._cache_key_rev(-34.6037, -58.3816)
        redis_client.setex(key, 86400, json.dumps({
            "lat": -34.6037, "lon": -58.3816,
            "display_name": "Buenos Aires",
        }))

        with patch("app.services.geocoding_service.requests.get") as mock_get:
            result = svc.reverse_geocode(-34.6037, -58.3816)
            mock_get.assert_not_called()

        assert result is not None
        assert "Buenos Aires" in result.display_name

    def test_fallback_without_redis(self):
        """Without Redis, geocode still works via HTTP."""
        svc = self._make_service(redis_client=None)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"lat": "-31.42", "lon": "-64.19", "display_name": "Córdoba"}
        ]

        with patch("app.services.geocoding_service.requests.get", return_value=mock_response):
            result = svc.geocode("cordoba")

        assert result is not None
        assert result.lat == pytest.approx(-31.42)
