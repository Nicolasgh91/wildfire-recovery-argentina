"""add_h3_index_to_fire_events

Revision ID: 6f0f3c2d7a9b
Revises: 5629d6e731ff
Create Date: 2026-02-02 18:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "6f0f3c2d7a9b"
down_revision: Union[str, None] = "5629d6e731ff"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("fire_events", sa.Column("h3_index", sa.BigInteger(), nullable=True))
    op.create_index("idx_fire_events_h3", "fire_events", ["h3_index"], unique=False)
    op.create_index(
        "idx_fire_events_h3_date",
        "fire_events",
        ["h3_index", "start_date"],
        unique=False,
    )
    op.execute(
        "COMMENT ON COLUMN fire_events.h3_index IS "
        "'H3 index (resolution 7-9) for efficient spatial aggregation. "
        "Computed from centroid using h3.geo_to_h3(lat, lon, resolution).'"
    )


def downgrade() -> None:
    op.drop_index("idx_fire_events_h3_date", table_name="fire_events")
    op.drop_index("idx_fire_events_h3", table_name="fire_events")
    op.drop_column("fire_events", "h3_index")
