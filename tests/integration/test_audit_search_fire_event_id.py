import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.api.auth_deps import get_current_user
from app.api.deps import get_db
from app.core.rate_limiter import check_rate_limit
from app.main import app
from app.models.user import User


def test_audit_search_includes_fire_event_id_for_episodes_with_events(db_session):
    """
    Contract test: /audit/search must return a non-null fire_event_id for
    episodes that have an associated fire_event via fire_episode_events.
    """
    # -- Override FastAPI dependencies --
    def override_get_db():
        yield db_session

    fake_user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        full_name="Test User",
        role="user",
    )

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[check_rate_limit] = lambda: None

    try:
        client = TestClient(app)

        # -- Seed test data --
        episode_id = uuid.uuid4()
        fire_event_id = uuid.uuid4()
        province = f"TestProv_{uuid.uuid4().hex[:8]}"

        db_session.execute(
            text(
                """
                INSERT INTO fire_episodes
                    (id, status, start_date, provinces, centroid_lat, centroid_lon)
                VALUES
                    (:eid, 'active', NOW(), ARRAY[:province], -42.0, -71.0)
                """
            ),
            {"eid": str(episode_id), "province": province},
        )
        db_session.execute(
            text(
                """
                INSERT INTO fire_events
                    (id, centroid, start_date, end_date, total_detections, max_frp)
                VALUES
                    (:fid,
                     ST_SetSRID(ST_MakePoint(-71.0, -42.0), 4326),
                     NOW(), NOW(), 1, 100.0)
                """
            ),
            {"fid": str(fire_event_id)},
        )
        db_session.execute(
            text(
                """
                INSERT INTO fire_episode_events (episode_id, event_id)
                VALUES (:eid, :fid)
                """
            ),
            {"eid": str(episode_id), "fid": str(fire_event_id)},
        )
        db_session.flush()

        # -- Call the endpoint searching by province --
        resp = client.get(
            "/api/v1/audit/search",
            params={"q": province, "limit": 5},
        )
        assert resp.status_code == 200, f"Unexpected status {resp.status_code}: {resp.text}"

        data = resp.json()
        assert len(data["episodes"]) == 1

        episode = data["episodes"][0]
        assert episode["id"] == str(episode_id)
        assert episode["fire_event_id"] is not None, (
            "fire_event_id must not be null for episodes with linked events"
        )
        assert episode["fire_event_id"] == str(fire_event_id)
    finally:
        app.dependency_overrides.clear()
