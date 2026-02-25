"""
Tests unitarios para EpisodeService._resolve_episode_status.

Modelo canonico (doble condicion para extinct):
  1. Active:    al menos 1 evento 'active'
  2. Extinct:   elapsed >= ventana_temporal  Y  todos los eventos 'extinct'
  3. Monitoring: cualquier otro caso
"""
import pytest
from datetime import datetime, timedelta, timezone

from app.services.episode_service import EpisodeService


class MockEpisodeService(EpisodeService):
    def __init__(self):
        self.db = None

    def _get_episode_window_hours(self) -> int:
        return 720  # 30 dias


@pytest.fixture
def service():
    return MockEpisodeService()


def now():
    return datetime.now(timezone.utc)


# -------------------------------------------------------------------------
# Regla 1: active si hay eventos active
# -------------------------------------------------------------------------

def test_active_when_any_event_active(service):
    """Al menos 1 evento active => episodio active (ignora tiempo)."""
    status = service._resolve_episode_status(
        event_statuses={"active", "extinct"},
        last_seen_at=now() - timedelta(days=40),
    )
    assert status == "active"


def test_active_single_event(service):
    """Episodio con un solo evento active."""
    status = service._resolve_episode_status(
        event_statuses={"active"},
        last_seen_at=now(),
    )
    assert status == "active"


def test_active_overrides_window(service):
    """Aunque se supero la ventana temporal, si hay evento active => active."""
    status = service._resolve_episode_status(
        event_statuses={"active", "monitoring"},
        last_seen_at=now() - timedelta(hours=800),  # > 720h
    )
    assert status == "active"


# -------------------------------------------------------------------------
# Regla 2: extinct requiere AMBAS condiciones
# -------------------------------------------------------------------------

def test_extinct_requires_both_conditions(service):
    """Extinct solo si ventana superada Y todos eventos extinct."""
    status = service._resolve_episode_status(
        event_statuses={"extinct", "extinct"},
        last_seen_at=now() - timedelta(hours=721),  # > 720h
    )
    assert status == "extinct"


def test_monitoring_all_extinct_but_within_window(service):
    """Todos eventos extinct pero dentro de la ventana => monitoring (periodo de gracia)."""
    status = service._resolve_episode_status(
        event_statuses={"extinct", "extinct"},
        last_seen_at=now() - timedelta(hours=500),  # < 720h
    )
    assert status == "monitoring"


def test_monitoring_window_exceeded_but_event_still_monitoring(service):
    """Ventana superada pero hay evento en 'monitoring' => monitoring (doble condicion protege)."""
    status = service._resolve_episode_status(
        event_statuses={"monitoring", "extinct"},
        last_seen_at=now() - timedelta(hours=800),  # > 720h
    )
    assert status == "monitoring"


def test_monitoring_no_active_within_window(service):
    """Sin eventos active, dentro de la ventana => monitoring."""
    status = service._resolve_episode_status(
        event_statuses={"monitoring", "extinct"},
        last_seen_at=now() - timedelta(hours=100),  # < 720h
    )
    assert status == "monitoring"


# -------------------------------------------------------------------------
# Edge cases
# -------------------------------------------------------------------------

def test_empty_events_within_window(service):
    """Sin eventos pero dentro de la ventana => monitoring (no hay extintos confirmados)."""
    status = service._resolve_episode_status(
        event_statuses=set(),
        last_seen_at=now() - timedelta(hours=100),
    )
    assert status == "monitoring"


def test_empty_events_window_exceeded(service):
    """Sin eventos y ventana superada => monitoring (all_events_extinct requiere bool(set)=True)."""
    status = service._resolve_episode_status(
        event_statuses=set(),
        last_seen_at=now() - timedelta(hours=800),
    )
    # set vacio: all_events_extinct = False (no hay eventos que confirmen extincion)
    assert status == "monitoring"


def test_fallback_to_start_date(service):
    """Usa start_date si last_seen_at es None."""
    status = service._resolve_episode_status(
        event_statuses={"extinct"},
        last_seen_at=None,
        start_date=now() - timedelta(days=35),  # > 30d y todos extinct
    )
    assert status == "extinct"


def test_fallback_to_start_date_within_window(service):
    """Usa start_date fallback dentro de la ventana => monitoring."""
    status = service._resolve_episode_status(
        event_statuses={"extinct"},
        last_seen_at=None,
        start_date=now() - timedelta(days=5),
    )
    assert status == "monitoring"


def test_no_dates_defaults_to_monitoring(service):
    """Sin last_seen_at ni start_date => monitoring (caso borde seguro)."""
    status = service._resolve_episode_status(
        event_statuses={"extinct"},
        last_seen_at=None,
        start_date=None,
    )
    assert status == "monitoring"


def test_custom_window_hours(service):
    """Se puede pasar window_hours explicitamente."""
    status = service._resolve_episode_status(
        event_statuses={"extinct"},
        last_seen_at=now() - timedelta(hours=49),
        window_hours=48,  # ventana de 48h
    )
    assert status == "extinct"


def test_timezone_naive_last_seen_is_treated_as_utc(service):
    """Timestamp sin timezone se trata como UTC (no debe lanzar excepcion)."""
    naive_dt = datetime.now() - timedelta(hours=800)
    status = service._resolve_episode_status(
        event_statuses={"extinct"},
        last_seen_at=naive_dt,
        window_hours=720,
    )
    assert status == "extinct"
