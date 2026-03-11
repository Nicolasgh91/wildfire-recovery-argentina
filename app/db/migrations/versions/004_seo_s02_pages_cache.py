# SEO-S-02: tabla seo_pages_cache

"""Create seo_pages_cache table

Revision ID: 004
Revises: 003
Create Date: 2026-03-10

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "seo_pages_cache",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("page_type", sa.Text(), nullable=False),
        sa.Column("slug", sa.Text(), nullable=False),
        sa.Column("cached_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stale_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("content", JSONB(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("page_type", "slug", name="uq_seo_pages_cache_page_type_slug"),
    )


def downgrade():
    op.drop_table("seo_pages_cache")
