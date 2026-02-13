"""fg_ep_23_enforce_fire_episodes_end_date_trigger

Revision ID: 488c97acc011
Revises: 7196f62a30d4
Create Date: 2026-02-13 18:45:31.262339

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '488c97acc011'
down_revision: Union[str, None] = '7196f62a30d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.enforce_episode_end_date()
        RETURNS trigger
        AS $$
        BEGIN
            IF NEW.status = 'closed' THEN
                NEW.end_date := COALESCE(NEW.end_date, NEW.last_seen_at, NOW());
            ELSE
                NEW.end_date := NULL;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    op.execute(
        """
        DROP TRIGGER IF EXISTS trg_enforce_episode_end_date
            ON public.fire_episodes
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_enforce_episode_end_date
        BEFORE INSERT OR UPDATE OF status, end_date, last_seen_at
            ON public.fire_episodes
        FOR EACH ROW
        EXECUTE FUNCTION public.enforce_episode_end_date()
        """
    )

    op.execute(
        """
        UPDATE public.fire_episodes
           SET end_date = COALESCE(end_date, last_seen_at, NOW())
         WHERE status = 'closed'
           AND end_date IS NULL
        """
    )
    op.execute(
        """
        UPDATE public.fire_episodes
           SET end_date = NULL
         WHERE status <> 'closed'
           AND end_date IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TRIGGER IF EXISTS trg_enforce_episode_end_date
            ON public.fire_episodes
        """
    )
    op.execute(
        """
        DROP FUNCTION IF EXISTS public.enforce_episode_end_date()
        """
    )
