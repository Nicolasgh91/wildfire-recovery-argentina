from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import text


def test_fire_events_data_has_no_legacy_statuses(db_session):
    count = db_session.execute(
        text(
            """
            SELECT COUNT(*)
            FROM public.fire_events
            WHERE status IN ('controlled', 'extinguished')
            """
        )
    ).scalar_one()

    assert count == 0


def test_fire_events_status_constraint_is_canonical(db_session):
    constraint = db_session.execute(
        text(
            """
            SELECT pg_get_constraintdef(oid)
            FROM pg_constraint
            WHERE conrelid = 'public.fire_events'::regclass
              AND conname = 'fire_events_status_check'
            """
        )
    ).scalar_one()

    definition = constraint.lower()
    assert "active" in definition
    assert "monitoring" in definition
    assert "extinct" in definition
    assert "controlled" not in definition
    assert "extinguished" not in definition


def test_fire_events_schema_uses_extinct_at_column(db_session):
    cols = db_session.execute(
        text(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'fire_events'
              AND column_name IN ('extinguished_at', 'extinct_at')
            ORDER BY column_name
            """
        )
    ).fetchall()

    names = [row[0] for row in cols]
    assert "extinct_at" in names
    assert "extinguished_at" not in names


def test_fire_events_rejects_legacy_status_values(db_session):
    with pytest.raises(Exception):
        db_session.execute(
            text(
                """
                INSERT INTO public.fire_events (
                    id,
                    centroid,
                    start_date,
                    end_date,
                    last_seen_at,
                    status,
                    total_detections,
                    created_at,
                    updated_at
                ) VALUES (
                    :id,
                    ST_GeomFromText('POINT(-58.4 -34.6)', 4326)::geography,
                    :start_date,
                    :end_date,
                    :last_seen_at,
                    'extinguished',
                    1,
                    NOW(),
                    NOW()
                )
                """
            ),
            {
                "id": str(uuid4()),
                "start_date": datetime.now(timezone.utc),
                "end_date": datetime.now(timezone.utc),
                "last_seen_at": datetime.now(timezone.utc),
            },
        )

    db_session.rollback()
