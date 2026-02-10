from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.core.config import settings
from app.main import app

# Mock keys
TEST_KEY = "test-api-key-123"
TEST_ADMIN_KEY = "test-admin-key-999"


@pytest.fixture
def client():
    # Patch settings to accept our test keys
    # Note: We patch app.core.security.settings AND app.core.rate_limiter.settings
    # to ensure consistency, though typically they point to same object.
    with patch("app.core.config.settings.API_KEY", SecretStr(TEST_KEY)), patch(
        "app.core.config.settings.ADMIN_API_KEY", SecretStr(TEST_ADMIN_KEY)
    ):
        with TestClient(app) as test_client:
            yield test_client


def test_audit_land_use_authenticated(client):
    """Regression: Audit endpoint should accept authorized requests."""
    # We pass strict validation args to avoid 422
    payload = {"lat": -31.4201, "lon": -64.1888, "radius_meters": 500}
    response = client.post(
        "/api/v1/audit/land-use", json=payload, headers={"X-API-Key": TEST_KEY}
    )
    # 200 OK means success.
    # 422 means validation error (schema check passed, logic validation failed).
    # 403 means Auth failed.
    assert response.status_code in [200, 422]
    assert response.status_code != 403


def test_certificates_issue_authenticated(client):
    """Regression: Certificates issue should accept authorized requests."""
    payload = {
        "fire_event_id": "550e8400-e29b-41d4-a716-446655440000",
        "issued_to": "Juan Perez",
        "requester_email": "juan@example.com",
    }
    response = client.post(
        "/api/v1/certificates/issue", json=payload, headers={"X-API-Key": TEST_KEY}
    )
    # Expect 200 (created/cached) or 404/400/422 (valid logic but data issue).
    # Should NOT be 403.
    assert response.status_code != 403


def test_reports_judicial_authenticated(client):
    """Regression: Judicial reports should accept authorized requests."""
    payload = {
        "fire_event_id": "550e8400-e29b-41d4-a716-446655440000",
        "requester_name": "Dr. Legal",
        "case_reference": "CASE-2026-001",
    }
    response = client.post(
        "/api/v1/reports/judicial", json=payload, headers={"X-API-Key": TEST_KEY}
    )
    assert response.status_code != 403


def test_reports_judicial_unauthenticated_blocked(client):
    """Security: Missing key should be blocked (403) on strictly protected endpoints."""
    # Reports endpoint depends on verify_api_key in main.py include
    payload = {"some": "data"}
    response = client.post("/api/v1/reports/judicial", json=payload)
    assert response.status_code == 403


def test_admin_endpoint_access(client):
    """Security: Admin endpoint accepts Admin key."""
    response = client.get(
        "/api/v1/citizen/reviews/all", headers={"X-API-Key": TEST_ADMIN_KEY}
    )
    assert response.status_code == 200


def test_admin_endpoint_blocks_user(client):
    """Security: Admin endpoint blocks User key."""
    response = client.get(
        "/api/v1/citizen/reviews/all", headers={"X-API-Key": TEST_KEY}
    )
    assert response.status_code == 403
