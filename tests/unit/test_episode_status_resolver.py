import pytest
from datetime import datetime, timedelta, timezone
from app.services.episode_service import EpisodeService

class MockEpisodeService(EpisodeService):
    def __init__(self):
        # Evitamos inicializar la conexion a la DB real para pruebas unitarias
        self.db = None
    
    def _get_episode_window_hours(self) -> int:
        return 720  # 30 días

@pytest.fixture
def service():
    return MockEpisodeService()

def test_resolve_status_active(service):
    # Rule 1: Si hay eventos activos, el episodio DEBE ser activo, ignorando el tiempo
    status = service._resolve_episode_status(
        event_statuses={"active", "extinct"},
        last_seen_at=datetime.now(timezone.utc) - timedelta(days=40)
    )
    assert status == "active"

def test_resolve_status_extinct(service):
    # Rule 2: Si no hay activos y superó la ventana temporal, es extinct
    status = service._resolve_episode_status(
        event_statuses={"extinct", "monitoring"},
        last_seen_at=datetime.now(timezone.utc) - timedelta(days=31) # 31 days > 30 days
    )
    assert status == "extinct"

def test_resolve_status_monitoring_within_window(service):
    # Rule 3: Si no hay activos pero está dentro de la ventana, es monitoring
    status = service._resolve_episode_status(
        event_statuses={"extinct"},
        last_seen_at=datetime.now(timezone.utc) - timedelta(days=29) # 29 days < 30 days
    )
    assert status == "monitoring"

def test_resolve_status_fallback_to_start_date(service):
    # Prueba de COALESCE: usa start_date si last_seen_at es nulo
    status_extinct = service._resolve_episode_status(
        event_statuses={"extinct"},
        last_seen_at=None,
        start_date=datetime.now(timezone.utc) - timedelta(days=35)
    )
    assert status_extinct == "extinct"
    
    status_monitoring = service._resolve_episode_status(
        event_statuses={"extinct"},
        last_seen_at=None,
        start_date=datetime.now(timezone.utc) - timedelta(days=5)
    )
    assert status_monitoring == "monitoring"

def test_resolve_status_no_dates(service):
    # Failsafe: cuando no hay last_seen_at ni start_date, default a monitoring
    status = service._resolve_episode_status(
        event_statuses={"extinct"},
        last_seen_at=None,
        start_date=None
    )
    assert status == "monitoring"
