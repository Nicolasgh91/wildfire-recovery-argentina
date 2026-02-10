"""extend_fire_episodes

Revision ID: 8a3c5b7d1e2f
Revises: f2a1c4d7e6b5
Create Date: 2026-02-02 19:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "8a3c5b7d1e2f"
down_revision: Union[str, None] = "f2a1c4d7e6b5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "fire_episodes",
        sa.Column(
            "clustering_version_id",
            sa.UUID(),
            sa.ForeignKey("clustering_versions.id"),
            nullable=True,
        ),
    )
    op.add_column(
        "fire_episodes",
        sa.Column(
            "requires_recalculation",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=True,
        ),
    )
    op.add_column(
        "fire_episodes",
        sa.Column("dnbr_severity", sa.Numeric(), nullable=True),
    )
    op.add_column(
        "fire_episodes",
        sa.Column("severity_class", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "fire_episodes",
        sa.Column("dnbr_calculated_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.execute(
        "CREATE INDEX idx_episodes_needs_recalc "
        "ON fire_episodes(requires_recalculation) "
        "WHERE requires_recalculation = true;"
    )
    op.execute(
        "CREATE INDEX idx_episodes_severity "
        "ON fire_episodes(dnbr_severity DESC) "
        "WHERE dnbr_severity IS NOT NULL;"
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION mark_episode_for_recalculation()
        RETURNS TRIGGER AS $$
        BEGIN
            IF (
                OLD.centroid IS DISTINCT FROM NEW.centroid OR
                (OLD.status != 'false_positive' AND NEW.status = 'false_positive')
            ) THEN
                UPDATE fire_episodes
                SET requires_recalculation = true
                WHERE id IN (
                    SELECT episode_id
                    FROM fire_episode_events
                    WHERE event_id = NEW.id
                );
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    op.execute(
        """
        CREATE TRIGGER trg_invalidate_episode_on_event_change
        AFTER UPDATE ON fire_events
        FOR EACH ROW EXECUTE FUNCTION mark_episode_for_recalculation();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_invalidate_episode_on_event_change ON fire_events;")
    op.execute("DROP FUNCTION IF EXISTS mark_episode_for_recalculation();")
    op.execute("DROP INDEX IF EXISTS idx_episodes_severity;")
    op.execute("DROP INDEX IF EXISTS idx_episodes_needs_recalc;")
    op.drop_column("fire_episodes", "dnbr_calculated_at")
    op.drop_column("fire_episodes", "severity_class")
    op.drop_column("fire_episodes", "dnbr_severity")
    op.drop_column("fire_episodes", "requires_recalculation")
    op.drop_column("fire_episodes", "clustering_version_id")
