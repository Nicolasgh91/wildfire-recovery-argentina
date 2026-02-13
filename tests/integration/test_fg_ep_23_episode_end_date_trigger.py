from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import text


def _insert_episode(
    db_session,
    *,
    episode_id,
    status: str,
    start_date: datetime,
    end_date: datetime | None,
    last_seen_at: datetime | None,
) -> None:
    db_session.execute(
        text(
            """
            INSERT INTO public.fire_episodes (
                id,
                status,
                start_date,
                end_date,
                last_seen_at,
                created_at,
                updated_at
            ) VALUES (
                :id,
                :status,
                :start_date,
                :end_date,
                :last_seen_at,
                NOW(),
                NOW()
            )
            """
        ),
        {
            "id": str(episode_id),
            "status": status,
            "start_date": start_date,
            "end_date": end_date,
            "last_seen_at": last_seen_at,
        },
    )


def _fetch_episode_end_date(db_session, episode_id):
    return (
        db_session.execute(
            text("SELECT end_date FROM public.fire_episodes WHERE id = :episode_id"),
            {"episode_id": str(episode_id)},
        )
        .scalar_one()
    )


def test_non_closed_episode_forces_end_date_to_null(db_session):
    episode_id = uuid4()
    now = datetime.now(timezone.utc)
    _insert_episode(
        db_session,
        episode_id=episode_id,
        status="active",
        start_date=now - timedelta(days=1),
        end_date=now,
        last_seen_at=now,
    )

    assert _fetch_episode_end_date(db_session, episode_id) is None


def test_closed_episode_sets_end_date_from_last_seen_at(db_session):
    episode_id = uuid4()
    now = datetime.now(timezone.utc)
    last_seen = now - timedelta(hours=3)
    _insert_episode(
        db_session,
        episode_id=episode_id,
        status="closed",
        start_date=now - timedelta(days=2),
        end_date=None,
        last_seen_at=last_seen,
    )

    assert _fetch_episode_end_date(db_session, episode_id) == last_seen


def test_closed_episode_without_dates_sets_end_date_to_now(db_session):
    episode_id = uuid4()
    now = datetime.now(timezone.utc)
    _insert_episode(
        db_session,
        episode_id=episode_id,
        status="closed",
        start_date=now - timedelta(days=2),
        end_date=None,
        last_seen_at=None,
    )

    end_date = _fetch_episode_end_date(db_session, episode_id)
    assert end_date is not None
    assert now - timedelta(minutes=1) <= end_date <= datetime.now(timezone.utc) + timedelta(minutes=1)
