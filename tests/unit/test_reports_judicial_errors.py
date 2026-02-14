from types import SimpleNamespace
from uuid import uuid4

import fastapi.testclient as _tc
import pytest
from fastapi import HTTPException

from app.api.auth_deps import get_current_user
from app.api.routes import reports as reports_module
from app.db.session import get_db
from app.main import app
from app.services.ers_service import ReportStatus


class DummyDB:
    def execute(self, *args, **kwargs):
        raise RuntimeError("db write failed")

    def commit(self):
        return None

    def rollback(self):
        return None


@pytest.fixture()
def user_stub():
    return SimpleNamespace(id=uuid4(), email="tester@example.com")


@pytest.fixture(autouse=True)
def clear_overrides():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def _set_common_overrides(user_stub):
    app.dependency_overrides[get_current_user] = lambda: user_stub
    app.dependency_overrides[get_db] = lambda: DummyDB()


def test_judicial_report_maps_fire_not_found_to_404(monkeypatch, user_stub):
    class FakeERSService:
        def __init__(self, db):
            self.db = db

        def generate_report(self, _request):
            return SimpleNamespace(
                status=ReportStatus.FAILED,
                error_message="Fire event not found: deadbeef",
            )

    monkeypatch.setattr(reports_module, "ERSService", FakeERSService)
    _set_common_overrides(user_stub)

    with _tc.TestClient(app) as client:
        response = client.post(
            "/api/v1/reports/judicial",
            json={"fire_event_id": "00000000-0000-0000-0000-000000000000"},
        )

    assert response.status_code == 404
    assert "Evento de incendio no encontrado" in response.json()["detail"]


def test_judicial_report_dependency_failure_returns_503_with_request_id(monkeypatch, user_stub):
    class FakeERSService:
        def __init__(self, db):
            self.db = db

        def generate_report(self, _request):
            return SimpleNamespace(
                status=ReportStatus.FAILED,
                error_message="fpdf2 not installed",
            )

    monkeypatch.setattr(reports_module, "ERSService", FakeERSService)
    _set_common_overrides(user_stub)

    with _tc.TestClient(app) as client:
        response = client.post(
            "/api/v1/reports/judicial",
            json={"fire_event_id": "00000000-0000-0000-0000-000000000000"},
            headers={"Origin": "http://localhost:5173"},
        )

    assert response.status_code == 503
    detail = response.json()["detail"]
    assert detail["message"].startswith("Report generation failed")
    assert detail.get("request_id")
    assert (
        response.headers.get("access-control-allow-origin")
        == "http://localhost:5173"
    )


def test_judicial_report_propagates_http_exception(monkeypatch, user_stub):
    class FakeERSService:
        def __init__(self, db):
            self.db = db

        def generate_report(self, _request):
            raise HTTPException(status_code=422, detail="invalid judicial payload")

    monkeypatch.setattr(reports_module, "ERSService", FakeERSService)
    _set_common_overrides(user_stub)

    with _tc.TestClient(app) as client:
        response = client.post(
            "/api/v1/reports/judicial",
            json={"fire_event_id": "00000000-0000-0000-0000-000000000000"},
        )

    assert response.status_code == 422
    assert response.json()["detail"] == "invalid judicial payload"


def test_judicial_report_success_ignores_metadata_persist_failure(monkeypatch, user_stub):
    class FakeERSService:
        def __init__(self, db):
            self.db = db

        def generate_report(self, _request):
            return SimpleNamespace(
                status=ReportStatus.COMPLETED,
                report_id="FG-JUD-TEST-1",
                verification_hash="abc123",
                pdf_url="https://example.com/r.pdf",
            )

    monkeypatch.setattr(reports_module, "ERSService", FakeERSService)
    _set_common_overrides(user_stub)

    with _tc.TestClient(app) as client:
        response = client.post(
            "/api/v1/reports/judicial",
            json={"fire_event_id": "00000000-0000-0000-0000-000000000000"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["report"]["report_id"] == "FG-JUD-TEST-1"
