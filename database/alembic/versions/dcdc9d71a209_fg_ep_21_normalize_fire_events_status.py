"""fg_ep_21_normalize_fire_events_status

Revision ID: dcdc9d71a209
Revises: a158030ab842
Create Date: 2026-02-13 18:34:58.029917

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'dcdc9d71a209'
down_revision: Union[str, None] = 'a158030ab842'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
          IF EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema='public'
              AND table_name='fire_events'
              AND column_name='extinguished_at'
          ) AND NOT EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema='public'
              AND table_name='fire_events'
              AND column_name='extinct_at'
          ) THEN
            ALTER TABLE public.fire_events
            RENAME COLUMN extinguished_at TO extinct_at;
          END IF;
        END $$;
        """
    )

    op.execute(
        """
        DO $$
        DECLARE
          r record;
        BEGIN
          FOR r IN
            SELECT conname
            FROM pg_constraint
            WHERE conrelid = 'public.fire_events'::regclass
              AND contype = 'c'
              AND pg_get_constraintdef(oid) ILIKE '%status%'
          LOOP
            EXECUTE format(
              'ALTER TABLE public.fire_events DROP CONSTRAINT IF EXISTS %I',
              r.conname
            );
          END LOOP;
        END $$;
        """
    )

    op.execute(
        """
        UPDATE public.fire_events
        SET status = 'monitoring'
        WHERE status = 'controlled'
        """
    )
    op.execute(
        """
        UPDATE public.fire_events
        SET status = 'extinct'
        WHERE status = 'extinguished'
        """
    )

    op.execute(
        """
        ALTER TABLE public.fire_events
          ADD CONSTRAINT fire_events_status_check
          CHECK (status IN ('active','monitoring','extinct'))
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        DECLARE
          r record;
        BEGIN
          FOR r IN
            SELECT conname
            FROM pg_constraint
            WHERE conrelid = 'public.fire_events'::regclass
              AND contype = 'c'
              AND pg_get_constraintdef(oid) ILIKE '%status%'
          LOOP
            EXECUTE format(
              'ALTER TABLE public.fire_events DROP CONSTRAINT IF EXISTS %I',
              r.conname
            );
          END LOOP;
        END $$;
        """
    )

    op.execute(
        """
        UPDATE public.fire_events
        SET status = 'extinguished'
        WHERE status = 'extinct'
        """
    )

    op.execute(
        """
        ALTER TABLE public.fire_events
          ADD CONSTRAINT fire_events_status_check
          CHECK (status IN ('active','controlled','monitoring','extinguished'))
        """
    )

    op.execute(
        """
        DO $$
        BEGIN
          IF EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema='public'
              AND table_name='fire_events'
              AND column_name='extinct_at'
          ) AND NOT EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema='public'
              AND table_name='fire_events'
              AND column_name='extinguished_at'
          ) THEN
            ALTER TABLE public.fire_events
            RENAME COLUMN extinct_at TO extinguished_at;
          END IF;
        END $$;
        """
    )
