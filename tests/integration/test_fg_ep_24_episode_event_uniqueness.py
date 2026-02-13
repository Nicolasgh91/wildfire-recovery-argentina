from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from geoalchemy2.elements import WKTElement
from sqlalchemy import text

from app.models.episode import FireEpisode
from app.models.fire import FireEvent
from app.services.episode_service import EpisodeService


def _make_event() -> FireEvent:
    now = datetime.now(timezone.utc)
    return FireEvent(
        id=uuid4(),
        start_date=now - timedelta(hours=2),
        end_date=now - timedelta(hours=1),
        last_seen_at=now - timedelta(hours=1),
        total_detections=2,
        status="active",
        province="Test",
        centroid=WKTElement("POINT(-58.4 -34.6)", srid=4326),
    )


def _make_episode(status: str = "active") -> FireEpisode:
    now = datetime.now(timezone.utc)
    return FireEpisode(
        id=uuid4(),
        status=status,
        start_date=now - timedelta(days=1),
        last_seen_at=now - timedelta(hours=1),
    )


def test_unique_event_id_rejects_multiple_episode_links(db_session):
    event = _make_event()
    episode_a = _make_episode()
    episode_b = _make_episode()
    db_session.add_all([event, episode_a, episode_b])
    db_session.commit()

    db_session.execute(
        text(
            """
            INSERT INTO fire_episode_events (episode_id, event_id, added_at)
            VALUES (:episode_id, :event_id, NOW())
            """
        ),
        {"episode_id": str(episode_a.id), "event_id": str(event.id)},
    )

    with pytest.raises(Exception):
        db_session.execute(
            text(
                """
                INSERT INTO fire_episode_events (episode_id, event_id, added_at)
                VALUES (:episode_id, :event_id, NOW())
                """
            ),
            {"episode_id": str(episode_b.id), "event_id": str(event.id)},
        )

    db_session.rollback()


def test_assign_event_reassigns_atomically_to_single_episode(db_session):
    event = _make_event()
    episode_a = _make_episode()
    episode_b = _make_episode()
    db_session.add_all([event, episode_a, episode_b])
    db_session.commit()

    db_session.execute(
        text(
            """
            INSERT INTO fire_episode_events (episode_id, event_id, added_at)
            VALUES (:episode_id, :event_id, NOW())
            """
        ),
        {"episode_id": str(episode_a.id), "event_id": str(event.id)},
    )

    service = EpisodeService(db_session)
    old_episode_ids = service.assign_event(episode_b.id, event.id)

    rows = db_session.execute(
        text(
            """
            SELECT episode_id
            FROM fire_episode_events
            WHERE event_id = :event_id
            """
        ),
        {"event_id": str(event.id)},
    ).fetchall()

    assert old_episode_ids == [episode_a.id]
    assert len(rows) == 1
    assert rows[0][0] == episode_b.id
