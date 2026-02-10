from datetime import datetime, timedelta, timezone
from uuid import uuid4

from geoalchemy2.elements import WKTElement

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
