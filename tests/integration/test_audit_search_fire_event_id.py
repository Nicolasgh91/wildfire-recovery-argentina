from uuid import UUID

from fastapi.testclient import TestClient

from app.main import app


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

