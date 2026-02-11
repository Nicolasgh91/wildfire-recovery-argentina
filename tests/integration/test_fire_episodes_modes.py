from datetime import datetime, timedelta, timezone

from app.models.episode import FireEpisode


def _create_episode(db_session, **kwargs):
    episode = FireEpisode(**kwargs)
    db_session.add(episode)
    db_session.commit()
    db_session.refresh(episode)
    return episode


def test_fire_episodes_mode_active_filters_status(client, db_session):
    now = datetime.now(timezone.utc)
    _create_episode(
        db_session,
        status="active",
        start_date=now - timedelta(days=2),
    )
    _create_episode(
        db_session,
        status="monitoring",
        start_date=now - timedelta(days=3),
    )
    _create_episode(
        db_session,
        status="closed",
        start_date=now - timedelta(days=5),
        end_date=now - timedelta(days=1),
    )

    response = client.get("/api/v1/fire-episodes?mode=active&page_size=10")
    assert response.status_code == 200
    data = response.json()
    statuses = {episode["status"] for episode in data["episodes"]}
    assert statuses.issubset({"active", "monitoring"})
    assert len(data["episodes"]) == 2


def test_fire_episodes_mode_recent_filters_by_end_date(client, db_session):
    now = datetime.now(timezone.utc)
    recent = _create_episode(
        db_session,
        status="closed",
        start_date=now - timedelta(days=15),
        end_date=now - timedelta(days=10),
    )
    _create_episode(
        db_session,
        status="closed",
        start_date=now - timedelta(days=120),
        end_date=now - timedelta(days=90),
    )
    _create_episode(
        db_session,
        status="active",
        start_date=now - timedelta(days=1),
    )

    response = client.get("/api/v1/fire-episodes?mode=recent&page_size=10")
    assert response.status_code == 200
    data = response.json()
    ids = {episode["id"] for episode in data["episodes"]}
    assert recent.id in ids
    assert len(data["episodes"]) == 1


def test_fire_episodes_mode_invalid_returns_400(client):
    response = client.get("/api/v1/fire-episodes?mode=invalid")
    assert response.status_code == 400
