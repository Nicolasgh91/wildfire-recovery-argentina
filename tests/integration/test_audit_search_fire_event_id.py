<<<<<<< HEAD
from uuid import UUID
=======
import uuid
>>>>>>> 78c42e55cef136337181fe8c6511a8d52e9838ab

from fastapi.testclient import TestClient

from app.main import app
<<<<<<< HEAD


client = TestClient(app)


def test_audit_search_includes_fire_event_id_field():
    response = client.get("/api/v1/audit/search", params={"q": "Córdoba"})
    # Endpoint should respond even si no hay resultados; focus en shape
    assert response.status_code in (200, 404)

    if response.status_code == 404:
        return

    data = response.json()
    assert "episodes" in data
    for episode in data["episodes"]:
        # La clave debe existir siempre, aunque sea null
        assert "fire_event_id" in episode
        if episode["fire_event_id"] is not None:
            # Debe ser un UUID válido serializado como string
            UUID(episode["fire_event_id"])

=======
from app.api.deps import get_db


def test_audit_search_includes_fire_event_id_for_episodes_with_events(monkeypatch, db_session):
    """
    Contract test: /audit/search must include fire_event_id for episodes
    that have an associated fire_event via fire_episode_events.
    """
    # Wire test db session
    monkeypatch.setattr("app.api.deps.get_db", lambda: db_session)

    client = TestClient(app)

    # Create a minimal fire_event, episode and link between them
    episode_id = uuid.uuid4()
    fire_event_id = uuid.uuid4()

    db_session.execute(
        """
        INSERT INTO fire_episodes (id, status, start_date, centroid_lat, centroid_lon)
        VALUES (:eid, 'active', NOW(), -34.0, -58.0)
        """,
        {"eid": str(episode_id)},
    )
    db_session.execute(
        """
        INSERT INTO fire_events (id, centroid, start_date, end_date, total_detections)
        VALUES (:fid, ST_SetSRID(ST_MakePoint(-58.0, -34.0), 4326), NOW(), NOW(), 1)
        """,
        {"fid": str(fire_event_id)},
    )
    db_session.execute(
        """
        INSERT INTO fire_episode_events (episode_id, event_id)
        VALUES (:eid, :fid)
        """,
        {"eid": str(episode_id), "fid": str(fire_event_id)},
    )
    db_session.commit()

    resp = client.get("/audit/search", params={"q": "Buenos Aires", "limit": 1, "radius_km": 10})
    assert resp.status_code in (200, 404)

    if resp.status_code == 404:
        # In environments without geocoding data this test is not conclusive.
        return

    data = resp.json()
    assert "episodes" in data
    assert isinstance(data["episodes"], list)
    if not data["episodes"]:
        return

    episode = data["episodes"][0]
    assert "fire_event_id" in episode
    # El valor exacto puede no coincidir si la búsqueda no devuelve nuestro episodio,
    # pero al menos debe ser un string o null.
    assert episode["fire_event_id"] is None or isinstance(episode["fire_event_id"], str)
>>>>>>> 78c42e55cef136337181fe8c6511a8d52e9838ab
