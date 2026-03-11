# SEO-S-04: tabla seo_minor_fire_quota

"""Create seo_minor_fire_quota table

Revision ID: 006
Revises: 005
Create Date: 2026-03-10

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY, UUID

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "seo_minor_fire_quota",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("year_month", sa.Text(), nullable=False),
        sa.Column("episode_ids", ARRAY(UUID(as_uuid=True)), nullable=False, server_default="{}"),
        sa.Column("url_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("year_month", name="uq_seo_minor_fire_quota_year_month"),
    )


def downgrade():
    op.drop_table("seo_minor_fire_quota")
