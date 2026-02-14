"""Tests for strict CORS policy (BL-004 / SEC-007)."""
import pytest
from types import SimpleNamespace
import anyio
import httpx

from app.api.auth_deps import get_current_user
from app.api.v1.explorations import get_exploration_service
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

    def test_preflight_allows_idempotency_key_for_exploration_generate(self, client):
        resp = client.request(
            "OPTIONS",
            "/api/v1/explorations/00000000-0000-0000-0000-000000000000/generate",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Authorization, Content-Type, Idempotency-Key",
            },
        )
        assert resp.status_code in (200, 204)
        allow_headers = resp.headers.get("access-control-allow-headers", "").lower()
        assert "idempotency-key" in allow_headers

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


class _ExplorationServiceCrashStub:
    def get_generation_status(self, *args, **kwargs):
        raise RuntimeError("boom")


def _get_with_no_raise(path: str, headers: dict[str, str]):
    async def _request():
        transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            return await client.get(path, headers=headers)

    return anyio.run(_request)


def test_global_error_includes_cors_headers_for_allowed_origin():
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id="00000000-0000-0000-0000-000000000001"
    )
    app.dependency_overrides[get_exploration_service] = (
        lambda: _ExplorationServiceCrashStub()
    )
    try:
        response = _get_with_no_raise(
            "/api/v1/explorations/00000000-0000-0000-0000-000000000000/generate/00000000-0000-0000-0000-000000000000",
            headers={"Origin": "http://localhost:5173"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 500
    assert response.json()["detail"] == "Internal Server Error"
    assert (
        response.headers.get("access-control-allow-origin")
        == "http://localhost:5173"
    )
    assert response.headers.get("access-control-allow-credentials") == "true"


def test_global_error_omits_cors_headers_for_disallowed_origin():
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id="00000000-0000-0000-0000-000000000001"
    )
    app.dependency_overrides[get_exploration_service] = (
        lambda: _ExplorationServiceCrashStub()
    )
    try:
        response = _get_with_no_raise(
            "/api/v1/explorations/00000000-0000-0000-0000-000000000000/generate/00000000-0000-0000-0000-000000000000",
            headers={"Origin": "http://malicious.example"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 500
    assert response.json()["detail"] == "Internal Server Error"
    assert "access-control-allow-origin" not in response.headers
