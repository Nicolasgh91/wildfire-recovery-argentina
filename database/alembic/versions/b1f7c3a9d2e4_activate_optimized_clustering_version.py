"""activate_optimized_clustering_version

Revision ID: b1f7c3a9d2e4
Revises: 8a3c5b7d1e2f
Create Date: 2026-02-11 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b1f7c3a9d2e4"
down_revision: Union[str, None] = "8a3c5b7d1e2f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("UPDATE clustering_versions SET is_active = false WHERE is_active = true;")
    op.execute(
        "INSERT INTO clustering_versions ("
        "version_name, epsilon_km, min_points, temporal_window_hours, algorithm, change_reason, is_active"
        ") VALUES ("
        "'v2.0-optimized', 2.5, 2, 48, 'ST-DBSCAN', 'T7.2 optimization', true"
        ")"
    )


def downgrade() -> None:
    op.execute("UPDATE clustering_versions SET is_active = false;")
    op.execute("DELETE FROM clustering_versions WHERE version_name = 'v2.0-optimized';")
    op.execute(
        """
        UPDATE clustering_versions
           SET is_active = true
         WHERE id = (
            SELECT id
              FROM clustering_versions
             ORDER BY created_at DESC NULLS LAST
             LIMIT 1
         );
        """
    )
