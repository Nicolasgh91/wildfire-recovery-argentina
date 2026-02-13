"""fg_ep_24_enforce_fire_episode_events_1n

Revision ID: af536f2a144a
Revises: 488c97acc011
Create Date: 2026-02-13 18:49:13.999740

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'af536f2a144a'
down_revision: Union[str, None] = '488c97acc011'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        WITH ranked AS (
            SELECT ctid,
                   ROW_NUMBER() OVER (
                     PARTITION BY event_id
                     ORDER BY added_at DESC NULLS LAST, episode_id
                   ) AS rn
            FROM public.fire_episode_events
        )
        DELETE FROM public.fire_episode_events fee
        USING ranked r
        WHERE fee.ctid = r.ctid
          AND r.rn > 1
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ux_fire_episode_events_event_id
            ON public.fire_episode_events (event_id)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ux_fire_episode_events_event_id")
