"""create_clustering_versions_table

Revision ID: 9d2a4e1f0c3b
Revises: 6f0f3c2d7a9b
Create Date: 2026-02-02 18:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "9d2a4e1f0c3b"
down_revision: Union[str, None] = "6f0f3c2d7a9b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "clustering_versions",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("version_name", sa.String(length=50), nullable=False),
        sa.Column("epsilon_km", sa.Numeric(), nullable=False),
        sa.Column("min_points", sa.Integer(), nullable=False),
        sa.Column("temporal_window_hours", sa.Integer(), nullable=False),
        sa.Column(
            "algorithm",
            sa.String(length=20),
            server_default=sa.text("'ST-DBSCAN'"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("change_reason", sa.Text()),
        sa.CheckConstraint("epsilon_km > 0 AND epsilon_km <= 100", name="clustering_versions_epsilon_km_check"),
        sa.CheckConstraint("min_points >= 1 AND min_points <= 100", name="clustering_versions_min_points_check"),
        sa.CheckConstraint(
            "temporal_window_hours >= 1 AND temporal_window_hours <= 168",
            name="clustering_versions_temporal_window_hours_check",
        ),
        sa.CheckConstraint(
            "algorithm IN ('DBSCAN', 'ST-DBSCAN', 'HDBSCAN')",
            name="clustering_versions_algorithm_check",
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "idx_clustering_versions_active",
        "clustering_versions",
        ["is_active"],
        unique=False,
        postgresql_where=sa.text("is_active = true"),
    )
    op.create_index(
        "idx_clustering_versions_single_active",
        "clustering_versions",
        ["is_active"],
        unique=True,
        postgresql_where=sa.text("is_active = true"),
    )

    op.execute(
        "INSERT INTO clustering_versions ("
        "version_name, epsilon_km, min_points, temporal_window_hours, algorithm, change_reason"
        ") VALUES ("
        "'v1.0-initial', 5.0, 3, 24, 'ST-DBSCAN', 'Configuracion inicial del sistema'"
        ")"
    )

    op.execute(
        "COMMENT ON TABLE clustering_versions IS "
        "'Stores clustering parameter versions for episode reproducibility. "
        "Each episode references the version used to generate it.'"
    )


def downgrade() -> None:
    op.drop_index("idx_clustering_versions_single_active", table_name="clustering_versions")
    op.drop_index("idx_clustering_versions_active", table_name="clustering_versions")
    op.drop_table("clustering_versions")
