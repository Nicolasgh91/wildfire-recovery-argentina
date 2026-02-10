"""create_h3_recurrence_stats_view

Revision ID: c3e2f9a1b8d0
Revises: b7e6c1a4d9f2
Create Date: 2026-02-02 18:50:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3e2f9a1b8d0"
down_revision: Union[str, None] = "b7e6c1a4d9f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE MATERIALIZED VIEW h3_recurrence_stats AS
        SELECT
            h3_index,
            COUNT(*) as total_fires,
            COUNT(*) FILTER (
                WHERE start_date > NOW() - INTERVAL '5 years'
            ) as fires_last_5_years,
            COUNT(*) FILTER (
                WHERE start_date > NOW() - INTERVAL '1 year'
            ) as fires_last_year,
            MAX(max_frp) as max_frp_ever,
            SUM(estimated_area_hectares) as total_hectares_burned,
            AVG(estimated_area_hectares) as avg_hectares_per_fire,
            CASE
                WHEN COUNT(*) FILTER (
                    WHERE start_date > NOW() - INTERVAL '5 years'
                ) > 3 THEN 'high'
                WHEN COUNT(*) FILTER (
                    WHERE start_date > NOW() - INTERVAL '5 years'
                ) >= 1 THEN 'medium'
                ELSE 'low'
            END as recurrence_class,
            LEAST(
                COUNT(*) FILTER (
                    WHERE start_date > NOW() - INTERVAL '5 years'
                )::NUMERIC / 5.0,
                1.0
            ) as recurrence_score,
            MAX(start_date) as last_fire_date,
            NOW() as calculated_at
        FROM fire_events
        WHERE h3_index IS NOT NULL
        GROUP BY h3_index;
        """
    )

    op.execute(
        "CREATE UNIQUE INDEX idx_h3_recurrence_h3 "
        "ON h3_recurrence_stats(h3_index);"
    )
    op.execute(
        "CREATE INDEX idx_h3_recurrence_class "
        "ON h3_recurrence_stats(recurrence_class);"
    )
    op.execute(
        "CREATE INDEX idx_h3_recurrence_score "
        "ON h3_recurrence_stats(recurrence_score DESC);"
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION refresh_h3_recurrence_stats()
        RETURNS void AS $$
        BEGIN
            REFRESH MATERIALIZED VIEW CONCURRENTLY h3_recurrence_stats;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    op.execute(
        "COMMENT ON MATERIALIZED VIEW h3_recurrence_stats IS "
        "'Fire recurrence statistics by H3 cell. "
        "Classification: high (>3/5yr), medium (1-3/5yr), low (<1/5yr). "
        "Refresh daily via pg_cron.'"
    )


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS refresh_h3_recurrence_stats();")
    op.execute("DROP INDEX IF EXISTS idx_h3_recurrence_score;")
    op.execute("DROP INDEX IF EXISTS idx_h3_recurrence_class;")
    op.execute("DROP INDEX IF EXISTS idx_h3_recurrence_h3;")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS h3_recurrence_stats;")
