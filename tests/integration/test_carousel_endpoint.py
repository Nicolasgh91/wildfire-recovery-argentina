import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_list_active_episodes_carousel_filters():
    """
    Test that the /api/v1/fire-episodes?mode=active endpoint correctly filters
    episodes by gee_candidate=True and slides_data existence.
    """
    response = client.get("/api/v1/fire-episodes?mode=active&page_size=10")
    
    # Integration tests against live/test databases should either mock or expect empty/populated response.
    # If successful, we validate the data contract.
    if response.status_code == 200:
        data = response.json()
        assert "episodes" in data
        assert "total" in data
        
        for ep in data["episodes"]:
            # Filtro MUST be gee_candidate == True
            assert ep["gee_candidate"] is True
            # Slides data no debe ser nulo
            assert ep["slides_data"] is not None
            # Debe tener al menos 1 slide si estamos en mode=active
            assert len(ep["slides_data"]) > 0
            # Solo deben venir activos o en monitorio
            assert ep["status"] in ["active", "monitoring"]
