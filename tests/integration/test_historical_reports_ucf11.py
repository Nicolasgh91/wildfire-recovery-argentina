import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.services.ers_service import ReportResult, ReportStatus, ReportType


class DummyIdempotencyManager:
    store: dict = {}

    def __init__(self, db):
        self.db = db

    async def get_cached_response(self, key, endpoint, request_data=None):
        if not key:
            return None
        return self.store.get((key, endpoint))

    async def cache_response(
        self, key, endpoint, request_data, status_code, response_body
    ):
        if not key:
            return
        self.store[(key, endpoint)] = {"status": status_code, "body": response_body}


def _mock_report_result() -> ReportResult:
    return ReportResult(
        report_id="RPT-HIST-20260203-TEST01",
        report_type=ReportType.HISTORICAL,
        status=ReportStatus.COMPLETED,
        pdf_url="https://storage.local/reports/historical/test.pdf",
        verification_hash="sha256:" + ("b" * 64),
        verification_url="https://forestguard.freedynamicdns.org/verify/RPT-HIST-20260203-TEST01",
        fire_events_found=3,
    )


def test_historical_report_integration(user_client, monkeypatch):
    from app.api.routes import reports as reports_module

    DummyIdempotencyManager.store = {}
    monkeypatch.setattr(reports_module, "IdempotencyManager", DummyIdempotencyManager)

    def _fake_generate_report(self, request):
        return _mock_report_result()

    monkeypatch.setattr(
        reports_module.ERSService, "generate_report", _fake_generate_report
    )

    payload = {
        "protected_area_name": "Parque Nacional Test",
        "start_date": "2025-01-01",
        "end_date": "2025-12-31",
        "language": "es",
    }
    response = user_client.post("/api/v1/reports/historical", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["fires_included"] == 3
    assert data["report"]["report_type"] == "historical"
    assert data["report"]["report_id"] == "RPT-HIST-20260203-TEST01"


def test_historical_report_idempotency_regression(user_client, monkeypatch):
    from app.api.routes import reports as reports_module

    DummyIdempotencyManager.store = {}
    monkeypatch.setattr(reports_module, "IdempotencyManager", DummyIdempotencyManager)

    def _fake_generate_report(self, request):
        return _mock_report_result()

    monkeypatch.setattr(
        reports_module.ERSService, "generate_report", _fake_generate_report
    )

    payload = {
        "protected_area_name": "Parque Nacional Test",
        "start_date": "2025-01-01",
        "end_date": "2025-12-31",
        "language": "es",
    }
    key = str(uuid4())
    api_key = user_client.headers.get("X-API-Key", "")
    headers = {"X-Idempotency-Key": key, "X-API-Key": api_key}

    response_1 = user_client.post(
        "/api/v1/reports/historical", json=payload, headers=headers
    )
    response_2 = user_client.post(
        "/api/v1/reports/historical", json=payload, headers=headers
    )

    assert response_1.status_code == 200
    assert response_2.status_code == 200
    assert response_2.headers.get("X-Idempotency-Replayed") == "true"
    assert response_2.json() == response_1.json()


@pytest.mark.skipif(
    os.getenv("RUN_PROD_READONLY_TESTS") != "1",
    reason="Set RUN_PROD_READONLY_TESTS=1 to enable production smoke tests.",
)
def test_historical_report_smoke():
    if not settings.API_KEY:
        pytest.skip("API key not configured")

    client = TestClient(app)
    response = client.post(
        "/api/v1/reports/historical",
        json={},
        headers={"X-API-Key": settings.API_KEY.get_secret_value()},
    )
    assert response.status_code == 422
