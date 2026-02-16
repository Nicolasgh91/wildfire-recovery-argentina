import logging
from datetime import datetime, timedelta, timezone

from app.services.episode_service import EpisodeService


def test_episode_status_resolution_does_not_map_controlled_to_monitoring(
    db_session, caplog
):
    service = EpisodeService(db_session)
    last_seen_at = datetime.now(timezone.utc)

    with caplog.at_level(logging.WARNING):
        status = service._resolve_episode_status(
            last_seen_at,
            {"controlled"},
            grace_hours=96,
        )

    assert status == "active"
    assert "Unknown fire_event statuses" in caplog.text


def test_episode_status_resolution_keeps_monitoring_for_canonical_status(db_session):
    service = EpisodeService(db_session)
    last_seen_at = datetime.now(timezone.utc)

    status = service._resolve_episode_status(
        last_seen_at,
        {"monitoring"},
        grace_hours=96,
    )

    assert status == "monitoring"


def test_episode_status_resolution_marks_extinct_when_grace_is_exceeded(db_session):
    service = EpisodeService(db_session)
    old_seen = datetime.now(timezone.utc) - timedelta(hours=200)

    status = service._resolve_episode_status(
        old_seen,
        {"active"},
        grace_hours=96,
    )

    assert status == "extinct"
