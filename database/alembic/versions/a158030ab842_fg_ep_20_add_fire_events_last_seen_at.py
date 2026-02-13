"""fg_ep_20_add_fire_events_last_seen_at

Revision ID: a158030ab842
Revises: a1b2c3d4e5f6
Create Date: 2026-02-13 18:21:30.298668

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'a158030ab842'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE public.fire_events
        ADD COLUMN IF NOT EXISTS last_seen_at timestamptz
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_fire_events_last_seen_at
            ON public.fire_events (last_seen_at DESC)
        """
    )
    op.execute(
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
    op.execute(
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
    op.execute(
        """
        DROP TRIGGER IF EXISTS trg_sync_fire_event_last_seen_at
            ON public.fire_detections
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_sync_fire_event_last_seen_at
        AFTER INSERT OR UPDATE OF fire_event_id, detected_at
            ON public.fire_detections
        FOR EACH ROW EXECUTE FUNCTION public.sync_fire_event_last_seen_at_from_detection()
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TRIGGER IF EXISTS trg_sync_fire_event_last_seen_at
            ON public.fire_detections
        """
    )
    op.execute(
        """
        DROP FUNCTION IF EXISTS public.sync_fire_event_last_seen_at_from_detection()
        """
    )
    op.execute("DROP INDEX IF EXISTS idx_fire_events_last_seen_at")
    op.execute(
        """
        ALTER TABLE public.fire_events
        DROP COLUMN IF EXISTS last_seen_at
        """
    )
