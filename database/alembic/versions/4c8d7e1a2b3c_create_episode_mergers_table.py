"""create_episode_mergers_table

Revision ID: 4c8d7e1a2b3c
Revises: 9d2a4e1f0c3b
Create Date: 2026-02-02 18:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "4c8d7e1a2b3c"
down_revision: Union[str, None] = "9d2a4e1f0c3b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "episode_mergers",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("absorbed_episode_id", sa.UUID(), nullable=False),
        sa.Column("absorbing_episode_id", sa.UUID(), nullable=False),
        sa.Column("merged_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("reason", sa.String(length=50), nullable=False),
        sa.Column("merged_by_version_id", sa.UUID(), nullable=True),
        sa.Column("notes", sa.Text()),
        sa.CheckConstraint(
            "reason IN ("
            "'spatial_overlap', "
            "'temporal_continuity', "
            "'manual_merge', "
            "'algorithm_update'"
            ")",
            name="episode_mergers_reason_check",
        ),
        sa.CheckConstraint(
            "absorbed_episode_id != absorbing_episode_id",
            name="episode_mergers_different_episodes_check",
        ),
        sa.ForeignKeyConstraint(
            ["absorbed_episode_id"],
            ["fire_episodes.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["absorbing_episode_id"],
            ["fire_episodes.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["merged_by_version_id"],
            ["clustering_versions.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "idx_episode_mergers_absorbed",
        "episode_mergers",
        ["absorbed_episode_id"],
        unique=False,
    )
    op.create_index(
        "idx_episode_mergers_absorbing",
        "episode_mergers",
        ["absorbing_episode_id"],
        unique=False,
    )
    op.create_index(
        "idx_episode_mergers_date",
        "episode_mergers",
        ["merged_at"],
        unique=False,
    )

    op.execute(
        "COMMENT ON TABLE episode_mergers IS "
        "'Registro historico de fusiones entre episodios. Permite rastrear "
        "por que un episodio desaparecio y cual lo absorbio.'"
    )


def downgrade() -> None:
    op.drop_index("idx_episode_mergers_date", table_name="episode_mergers")
    op.drop_index("idx_episode_mergers_absorbing", table_name="episode_mergers")
    op.drop_index("idx_episode_mergers_absorbed", table_name="episode_mergers")
    op.drop_table("episode_mergers")
