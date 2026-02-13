from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import text


def _ensure_last_seen_infra(db_session) -> None:
    db_session.execute(
        text(
            """
            ALTER TABLE public.fire_events
            ADD COLUMN IF NOT EXISTS last_seen_at timestamptz
            """
        )
    )
    db_session.execute(
        text(
            """
            CREATE OR REPLACE FUNCTION public.sync_fire_event_last_seen_at_from_detection()
            RETURNS trigger
            AS $$
            DECLARE
                old_event_max timestamptz;
            BEGIN
                IF TG_OP = 'UPDATE'
                   AND OLD.fire_event_id IS NOT NULL
                   AND (
                        NEW.fire_event_id IS DISTINCT FROM OLD.fire_event_id
                        OR NEW.detected_at IS DISTINCT FROM OLD.detected_at
                   ) THEN
                    SELECT MAX(d.detected_at)
                      INTO old_event_max
                      FROM public.fire_detections d
                     WHERE d.fire_event_id = OLD.fire_event_id;

                    UPDATE public.fire_events e
                       SET last_seen_at = old_event_max
                     WHERE e.id = OLD.fire_event_id;
                END IF;

                IF NEW.fire_event_id IS NOT NULL THEN
                    UPDATE public.fire_events e
                       SET last_seen_at = CASE
                            WHEN e.last_seen_at IS NULL THEN NEW.detected_at
                            ELSE GREATEST(e.last_seen_at, NEW.detected_at)
                        END
                     WHERE e.id = NEW.fire_event_id;
                END IF;

                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql
            """
        )
    )
    db_session.execute(
        text(
            """
            DROP TRIGGER IF EXISTS trg_sync_fire_event_last_seen_at
              ON public.fire_detections
            """
        )
    )
    db_session.execute(
        text(
            """
            CREATE TRIGGER trg_sync_fire_event_last_seen_at
            AFTER INSERT OR UPDATE OF fire_event_id, detected_at
              ON public.fire_detections
            FOR EACH ROW EXECUTE FUNCTION public.sync_fire_event_last_seen_at_from_detection()
            """
        )
    )


def _insert_fire_event(
    db_session,
    *,
    event_id,
    start_date: datetime,
    end_date: datetime,
    last_seen_at: datetime | None,
) -> None:
    db_session.execute(
        text(
            """
            INSERT INTO fire_events (
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
                'active',
                1,
                NOW(),
                NOW()
            )
            """
        ),
        {
            "id": str(event_id),
            "start_date": start_date,
            "end_date": end_date,
            "last_seen_at": last_seen_at,
        },
    )


def _insert_detection(
    db_session,
    *,
    detection_id,
    event_id,
    detected_at: datetime,
) -> None:
    db_session.execute(
        text(
            """
            INSERT INTO fire_detections (
                id,
                satellite,
                instrument,
                detected_at,
                location,
                latitude,
                longitude,
                h3_index,
                fire_event_id,
                is_processed
            ) VALUES (
                :id,
                'VIIRS',
                'VIIRS',
                :detected_at,
                ST_GeomFromText('POINT(-58.4 -34.6)', 4326)::geography,
                -34.6,
                -58.4,
                0,
                :fire_event_id,
                true
            )
            """
        ),
        {
            "id": str(detection_id),
            "detected_at": detected_at,
            "fire_event_id": str(event_id),
        },
    )


def _fetch_last_seen_at(db_session, event_id):
    return (
        db_session.execute(
            text("SELECT last_seen_at FROM fire_events WHERE id = :event_id"),
            {"event_id": str(event_id)},
        )
        .scalar_one()
    )


def test_backfill_sets_last_seen_at_from_detection_max(db_session):
    _ensure_last_seen_infra(db_session)

    event_id = uuid4()
    t1 = datetime(2026, 2, 10, 10, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 2, 10, 12, 0, tzinfo=timezone.utc)

    _insert_fire_event(
        db_session,
        event_id=event_id,
        start_date=t1,
        end_date=t1,
        last_seen_at=None,
    )
    _insert_detection(db_session, detection_id=uuid4(), event_id=event_id, detected_at=t1)
    _insert_detection(db_session, detection_id=uuid4(), event_id=event_id, detected_at=t2)

    db_session.execute(
        text(
            """
            UPDATE public.fire_events e
               SET last_seen_at = q.max_detected_at
              FROM (
                    SELECT d.fire_event_id, MAX(d.detected_at) AS max_detected_at
                      FROM public.fire_detections d
                     WHERE d.fire_event_id IS NOT NULL
                  GROUP BY d.fire_event_id
                   ) q
             WHERE e.id = q.fire_event_id
               AND (e.last_seen_at IS NULL OR e.last_seen_at <> q.max_detected_at)
            """
        )
    )

    assert _fetch_last_seen_at(db_session, event_id) == t2


def test_trigger_updates_last_seen_at_using_greatest(db_session):
    _ensure_last_seen_infra(db_session)

    event_id = uuid4()
    base = datetime(2026, 2, 11, 8, 0, tzinfo=timezone.utc)
    older = datetime(2026, 2, 11, 7, 30, tzinfo=timezone.utc)
    newer = datetime(2026, 2, 11, 9, 15, tzinfo=timezone.utc)

    _insert_fire_event(
        db_session,
        event_id=event_id,
        start_date=base,
        end_date=base,
        last_seen_at=base,
    )

    _insert_detection(
        db_session,
        detection_id=uuid4(),
        event_id=event_id,
        detected_at=older,
    )
    assert _fetch_last_seen_at(db_session, event_id) == base

    _insert_detection(
        db_session,
        detection_id=uuid4(),
        event_id=event_id,
        detected_at=newer,
    )
    assert _fetch_last_seen_at(db_session, event_id) == newer
