"""
Reports Auth Contract Tests
============================
Verify that report generation endpoints (UC-02, UC-11) require
Supabase JWT authentication and reject requests without valid credentials.

These are unit-level tests: auth rejection happens before any DB query,
so no real database connection is needed.

CI smoke local values are set by auth-jwt-ci.yml; do not replace with
production values.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=False)


REPORTS_BASE = "/api/v1/reports"


def _bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _api_key(key: str) -> dict:
    return {"X-API-Key": key}


class TestReportsRequireJWT:
    """All /api/v1/reports/* endpoints must require Supabase JWT."""

    def test_post_judicial_no_token_returns_401(self):
        """POST /reports/judicial without Bearer token → 401."""
        resp = client.post(
            f"{REPORTS_BASE}/judicial",
            json={
                "fire_event_id": "00000000-0000-0000-0000-000000000001",
                "report_type": "full_forensic",
            },
        )
        assert resp.status_code == 401

    def test_post_judicial_invalid_token_returns_401(self):
        """POST /reports/judicial with invalid Bearer token → 401."""
        resp = client.post(
            f"{REPORTS_BASE}/judicial",
            json={
                "fire_event_id": "00000000-0000-0000-0000-000000000001",
                "report_type": "full_forensic",
            },
            headers=_bearer("not.a.valid.jwt"),
        )
        assert resp.status_code == 401

    def test_post_judicial_api_key_returns_401(self):
        """POST /reports/judicial with X-API-Key (wrong type) → 401."""
        resp = client.post(
            f"{REPORTS_BASE}/judicial",
            json={
                "fire_event_id": "00000000-0000-0000-0000-000000000001",
            },
            headers=_api_key("ci-test-api-key-not-for-production"),
        )
        assert resp.status_code == 401

    def test_post_historical_no_token_returns_401(self):
        """POST /reports/historical without Bearer token → 401."""
        resp = client.post(
            f"{REPORTS_BASE}/historical",
            json={
                "protected_area_name": "Nahuel Huapi",
                "start_date": "2020-01-01",
                "end_date": "2020-12-31",
            },
        )
        assert resp.status_code == 401

    def test_get_report_by_id_no_token_returns_401(self):
        """GET /reports/{id} without Bearer token → 401."""
        resp = client.get(
            f"{REPORTS_BASE}/00000000-0000-0000-0000-000000000001",
        )
        assert resp.status_code == 401

    def test_401_responses_include_www_authenticate(self):
        """RFC 6750: 401 on JWT-protected endpoint must include WWW-Authenticate: Bearer."""
        resp = client.post(
            f"{REPORTS_BASE}/judicial",
            json={"fire_event_id": "00000000-0000-0000-0000-000000000001"},
        )
        assert resp.status_code == 401
        assert "bearer" in resp.headers.get("WWW-Authenticate", "").lower()
