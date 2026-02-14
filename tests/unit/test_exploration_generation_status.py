from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import UUID, uuid4

import fastapi.testclient as _tc
import pytest

from app.api.auth_deps import get_current_user
from app.api.v1.explorations import get_exploration_service
from app.main import app


class DummyExplorationService:
    def __init__(self, mode: str = "ok"):
        self.mode = mode

    def get_generation_status(self, user_id: UUID, investigation_id: UUID, job_id: UUID):
        if self.mode == "investigation_not_found":
            raise ValueError("investigation_not_found")
        if self.mode == "job_not_found":
            raise ValueError("job_not_found")

        job = SimpleNamespace(
            id=job_id,
            investigation_id=investigation_id,
            status="processing",
            progress_done=2,
            progress_total=4,
            finished_at=None,
            started_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
        )
        return job, 50, 1


@pytest.fixture()
def user_stub():
    return SimpleNamespace(id=uuid4())


@pytest.fixture()
def exploration_ids():
    return uuid4(), uuid4()


def _override_user(user_stub):
    return user_stub


def _override_service(mode: str):
    return DummyExplorationService(mode=mode)


def test_generation_status_success(user_stub, exploration_ids):
    investigation_id, job_id = exploration_ids
    app.dependency_overrides[get_current_user] = lambda: _override_user(user_stub)
    app.dependency_overrides[get_exploration_service] = lambda: _override_service("ok")

    try:
        with _tc.TestClient(app) as client:
            response = client.get(
                f"/api/v1/explorations/{investigation_id}/generate/{job_id}"
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["job_id"] == str(job_id)
    assert payload["investigation_id"] == str(investigation_id)
    assert payload["status"] == "processing"
    assert payload["progress_done"] == 2
    assert payload["progress_total"] == 4
    assert payload["progress_pct"] == 50
    assert payload["failed_items"] == 1


@pytest.mark.parametrize("mode", ["investigation_not_found", "job_not_found"])
def test_generation_status_not_found(user_stub, exploration_ids, mode):
    investigation_id, job_id = exploration_ids
    app.dependency_overrides[get_current_user] = lambda: _override_user(user_stub)
    app.dependency_overrides[get_exploration_service] = lambda: _override_service(mode)

    try:
        with _tc.TestClient(app) as client:
            response = client.get(
                f"/api/v1/explorations/{investigation_id}/generate/{job_id}"
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["detail"] == "Generacion no encontrada"
