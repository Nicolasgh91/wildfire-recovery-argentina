from types import SimpleNamespace
from uuid import uuid4

import fastapi.testclient as _tc
import pytest

from app.api.auth_deps import get_current_user
from app.api.v1 import explorations as explorations_module
from app.api.v1.explorations import get_exploration_service
from app.main import app


class _GenerateServiceStub:
    def __init__(self, mode: str):
        self.mode = mode

    def generate_images(self, **kwargs):
        if self.mode == "crash":
            raise RuntimeError("db down")
        job = SimpleNamespace(
            id=uuid4(),
            status="queued",
            progress_total=3,
        )
        return job, 3, 7

    def list_items(self, investigation_id):
        return []


@pytest.fixture(autouse=True)
def clear_overrides():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def test_generate_returns_503_when_celery_enqueue_fails(monkeypatch):
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=uuid4())
    app.dependency_overrides[get_exploration_service] = lambda: _GenerateServiceStub(
        mode="ok"
    )

    def _raise_delay(_job_id):
        raise RuntimeError("redis unavailable")

    monkeypatch.setattr(explorations_module.generate_exploration_hd, "delay", _raise_delay)

    with _tc.TestClient(app) as client:
        response = client.post(
            f"/api/v1/explorations/{uuid4()}/generate",
            headers={
                "Origin": "http://localhost:5173",
                "Idempotency-Key": "idem-1",
            },
        )

    assert response.status_code == 503
    detail = response.json()["detail"]
    assert detail["message"] == "No se pudo iniciar la generacion"
    assert detail.get("request_id")
    assert (
        response.headers.get("access-control-allow-origin")
        == "http://localhost:5173"
    )


def test_generate_returns_503_when_service_raises_unexpected_error():
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=uuid4())
    app.dependency_overrides[get_exploration_service] = lambda: _GenerateServiceStub(
        mode="crash"
    )

    with _tc.TestClient(app) as client:
        response = client.post(
            f"/api/v1/explorations/{uuid4()}/generate",
            headers={
                "Origin": "http://localhost:5173",
                "Idempotency-Key": "idem-2",
            },
        )

    assert response.status_code == 503
    detail = response.json()["detail"]
    assert detail["message"] == "No se pudo iniciar la generacion"
    assert detail.get("request_id")
    assert (
        response.headers.get("access-control-allow-origin")
        == "http://localhost:5173"
    )
