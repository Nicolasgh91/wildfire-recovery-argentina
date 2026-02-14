"""Tests that /reports/* endpoints return 401 without valid JWT (BL-001)."""
import pytest

from app.main import app

# Use the CompatTestClient from conftest (patched into fastapi.testclient)
import fastapi.testclient as _tc


@pytest.fixture()
def anon_client():
    """Client with NO auth headers at all."""
    with _tc.TestClient(app) as c:
        yield c


class TestReportsAuth:
    """All /reports endpoints must reject unauthenticated requests."""

    def test_judicial_requires_auth(self, anon_client):
        resp = anon_client.post(
            "/api/v1/reports/judicial",
            json={"fire_event_id": "00000000-0000-0000-0000-000000000000"},
        )
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"

    def test_historical_requires_auth(self, anon_client):
        resp = anon_client.post(
            "/api/v1/reports/historical",
            json={
                "protected_area_id": "00000000-0000-0000-0000-000000000000",
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
            },
        )
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"

    def test_verify_requires_auth(self, anon_client):
        resp = anon_client.get(
            "/api/v1/reports/fake-id/verify",
            params={"hash_to_verify": "abc123"},
        )
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"
