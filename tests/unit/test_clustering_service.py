from datetime import datetime, timedelta, timezone
from uuid import uuid4

from geoalchemy2.elements import WKTElement

import app.services.clustering_service as clustering_service_module
from app.models.episode import FireEpisodeEvent
from app.models.fire import FireEvent
from app.services.clustering_service import ClusteringService


def _make_event(lat: float, lon: float, days_ago: int = 1):
    event_id = uuid4()
    start_date = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return FireEvent(
        id=event_id,
        start_date=start_date,
        end_date=start_date + timedelta(hours=2),
        total_detections=1,
        is_significant=False,
        province="Test",
        centroid=WKTElement(f"POINT({lon} {lat})", srid=4326),
    )


def test_clustering_groups_close_events(db_session):
    event_a = _make_event(lat=0.0, lon=0.0)
    event_b = _make_event(lat=0.001, lon=0.001)
    db_session.add_all([event_a, event_b])
    db_session.commit()

    service = ClusteringService(db_session)
    service.run_clustering(days_back=2, max_events=50)

    rows = (
        db_session.query(FireEpisodeEvent.episode_id)
        .filter(FireEpisodeEvent.event_id.in_([event_a.id, event_b.id]))
        .distinct()
        .all()
    )
    assert len(rows) == 1


def test_clustering_separates_far_events(db_session):
    event_a = _make_event(lat=0.0, lon=0.0)
    event_b = _make_event(lat=30.0, lon=30.0)
    db_session.add_all([event_a, event_b])
    db_session.commit()

    service = ClusteringService(db_session)
    service.run_clustering(days_back=2, max_events=50)

    rows = (
        db_session.query(FireEpisodeEvent.episode_id)
        .filter(FireEpisodeEvent.event_id.in_([event_a.id, event_b.id]))
        .distinct()
        .all()
    )
    assert len(rows) == 2


def test_clustering_uses_canonical_episode_parameters(db_session, monkeypatch):
    event = _make_event(lat=0.0, lon=0.0)
    db_session.add(event)
    db_session.commit()

    service = ClusteringService(db_session)
    captured: dict[str, float | int] = {}

    def _capture_candidates(_event, *, epsilon_meters, temporal_window_hours):
        captured["epsilon_meters"] = epsilon_meters
        captured["temporal_window_hours"] = temporal_window_hours
        return []

    monkeypatch.setattr(service, "_find_candidate_episodes", _capture_candidates)
    monkeypatch.setattr(
        clustering_service_module,
        "load_canonical_episode_flow_parameters",
        lambda _db: {
            "event_spatial_epsilon_meters": 2000.0,
            "event_temporal_window_hours": 48,
            "event_monitoring_window_hours": 168,
            "episode_spatial_epsilon_meters": 1234.0,
            "episode_temporal_window_hours": 12,
        },
    )

    service.run_clustering(days_back=2, max_events=50)

    assert captured["epsilon_meters"] == 1234.0
    assert captured["temporal_window_hours"] == 12
