"""
BL-007 — Auth Matrix Contract Tests
=====================================
Verify that each endpoint class enforces the correct authentication type.

Rules under test:
  - Public endpoints  : no credentials required  → 200/422/404
  - JWT endpoints     : Supabase Bearer required  → 401 when absent or invalid
  - API-key endpoints : X-API-Key required        → 403 when absent

These are unit-level tests: all auth checks are resolved before any DB query
is executed, so no real database connection is needed.

CI smoke local values are set by auth-jwt-ci.yml; do not replace with
production values.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _api_key(key: str) -> dict:
    return {"X-API-Key": key}


# ---------------------------------------------------------------------------
# 1. Public endpoints — no auth required
# ---------------------------------------------------------------------------

class TestPublicEndpoints:
    def test_root_health_is_200(self):
        """GET /health must return 200 for any client without credentials."""
        resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "healthy"

    def test_root_health_has_no_auth_header_requirement(self):
        """WWW-Authenticate header must NOT be present on public health endpoint."""
        resp = client.get("/health")
        assert "WWW-Authenticate" not in resp.headers


# ---------------------------------------------------------------------------
# 2. JWT-protected endpoints (audit router) — must return 401 when:
#    a) no Authorization header
#    b) invalid Bearer token
#    c) only X-API-Key provided (wrong auth scheme)
# ---------------------------------------------------------------------------

AUDIT_GEOCODE_URL = "/api/v1/audit/geocode"


class TestAuditEndpointAuthRequirement:
    """GET /api/v1/audit/geocode requires a valid Supabase JWT Bearer token."""

    def test_no_credentials_returns_401(self):
        """BL-007: Missing Authorization header → 401."""
        resp = client.get(AUDIT_GEOCODE_URL, params={"q": "chubut"})
        assert resp.status_code == 401

    def test_no_credentials_returns_www_authenticate_bearer(self):
        """RFC 6750: 401 response must include WWW-Authenticate: Bearer."""
        resp = client.get(AUDIT_GEOCODE_URL, params={"q": "chubut"})
        assert resp.status_code == 401
        assert "bearer" in resp.headers.get("WWW-Authenticate", "").lower()

    def test_invalid_bearer_token_returns_401(self):
        """BL-007: Malformed or unsigned Bearer token → 401."""
        resp = client.get(
            AUDIT_GEOCODE_URL,
            params={"q": "chubut"},
            headers=_bearer("this-is-not-a-valid-jwt"),
        )
        assert resp.status_code == 401

    def test_api_key_alone_on_jwt_endpoint_returns_401(self):
        """BL-007: X-API-Key on a JWT endpoint is not a valid credential → 401."""
        resp = client.get(
            AUDIT_GEOCODE_URL,
            params={"q": "chubut"},
            headers=_api_key("ci-test-api-key-not-for-production"),
        )
        assert resp.status_code == 401

    def test_empty_bearer_returns_401(self):
        """Empty Bearer token string → 401."""
        resp = client.get(
            AUDIT_GEOCODE_URL,
            params={"q": "chubut"},
            headers={"Authorization": "Bearer "},
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# 3. API-key-protected endpoints — must return 403 when no X-API-Key present
# ---------------------------------------------------------------------------

class TestApiKeyEndpointsRequireKey:
    """Endpoints mounted with verify_api_key must return 403 without the key."""

    def test_alerts_without_key_returns_403(self):
        """POST /api/v1/alerts/park-capacity without API key → 403."""
        resp = client.post("/api/v1/alerts/park-capacity", json={})
        assert resp.status_code == 403

    def test_historical_without_key_returns_403(self):
        """GET /api/v1/historical/ without API key → 403."""
        resp = client.get("/api/v1/historical/")
        assert resp.status_code == 403

    def test_metrics_without_key_returns_403(self):
        """GET /api/v1/metrics without API key → 403."""
        resp = client.get("/api/v1/metrics")
        assert resp.status_code == 403

    def test_workers_without_key_returns_403(self):
        """POST /api/v1/workers/detect-land-use without API key → 403."""
        resp = client.post("/api/v1/workers/detect-land-use", json={})
        assert resp.status_code == 403

    def test_jwt_not_accepted_on_api_key_endpoint(self):
        """Bearer JWT on an API-key endpoint is ignored — still 403."""
        resp = client.get(
            "/api/v1/historical/",
            headers=_bearer("fake-jwt-token"),
        )
        assert resp.status_code == 403
