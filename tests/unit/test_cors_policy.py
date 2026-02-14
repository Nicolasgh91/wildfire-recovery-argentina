"""Tests for strict CORS policy (BL-004 / SEC-007)."""
import pytest

from app.main import app

import fastapi.testclient as _tc


@pytest.fixture()
def client():
    with _tc.TestClient(app) as c:
        yield c


class TestCorsPolicy:
    """Verify CORS middleware uses explicit methods/headers, not wildcards."""

    def test_preflight_allowed_method(self, client):
        resp = client.request(
            "OPTIONS",
            "/api/v1/fires",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Authorization",
            },
        )
        # Should succeed (200 or 204)
        assert resp.status_code in (200, 204), f"Preflight failed: {resp.status_code}"
        assert "access-control-allow-origin" in resp.headers

    def test_preflight_allowed_headers(self, client):
        resp = client.request(
            "OPTIONS",
            "/api/v1/fires",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Authorization, Content-Type, X-API-Key",
            },
        )
        assert resp.status_code in (200, 204)

    def test_preflight_allows_skip_auth_redirect_header(self, client):
        resp = client.request(
            "OPTIONS",
            "/api/v1/fire-events/search",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "X-Skip-Auth-Redirect",
            },
        )
        assert resp.status_code in (200, 204)

    def test_expose_headers_present(self, client):
        resp = client.get(
            "/health",
            headers={"Origin": "http://localhost:5173"},
        )
        expose = resp.headers.get("access-control-expose-headers", "")
        assert "x-request-id" in expose.lower()

    def test_no_wildcard_methods_in_config(self):
        from app.core.config import settings

        assert "*" not in settings.ALLOWED_METHODS

    def test_no_wildcard_headers_in_config(self):
        from app.core.config import settings

        assert "*" not in settings.ALLOWED_HEADERS

    def test_skip_auth_redirect_present_in_config(self):
        from app.core.config import settings

        assert "X-Skip-Auth-Redirect" in settings.ALLOWED_HEADERS
