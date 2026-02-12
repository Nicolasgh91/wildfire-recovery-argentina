"""cleanup_recent_status_add_indexes

Revision ID: a1b2c3d4e5f6
Revises: b1f7c3a9d2e4
Create Date: 2026-02-12 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "b1f7c3a9d2e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("UPDATE fire_episodes SET status = 'extinct' WHERE status = 'recent'")
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_fire_episodes_status ON fire_episodes(status)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_fire_episodes_provinces ON fire_episodes USING gin(provinces)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_fire_episodes_gee_active ON fire_episodes(gee_candidate) WHERE gee_candidate = true"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_fire_events_province ON fire_events(province)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_fire_episodes_status_priority ON fire_episodes(status, gee_priority DESC NULLS LAST, start_date DESC NULLS LAST)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_fire_episodes_status_priority")
    op.execute("DROP INDEX IF EXISTS idx_fire_events_province")
    op.execute("DROP INDEX IF EXISTS idx_fire_episodes_gee_active")
    op.execute("DROP INDEX IF EXISTS idx_fire_episodes_provinces")
    op.execute("DROP INDEX IF EXISTS idx_fire_episodes_status")
