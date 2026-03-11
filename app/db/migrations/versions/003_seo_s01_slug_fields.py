# SEO-S-01: slug y campos SEO en fire_episodes

"""Add slug, seo_title, seo_description to fire_episodes

Revision ID: 003
Revises: 002
Create Date: 2026-03-10

"""
import sqlalchemy as sa
from alembic import op

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("fire_episodes", sa.Column("slug", sa.Text(), nullable=True))
    op.add_column("fire_episodes", sa.Column("seo_title", sa.Text(), nullable=True))
    op.add_column("fire_episodes", sa.Column("seo_description", sa.Text(), nullable=True))
    op.create_index("idx_fire_episodes_slug", "fire_episodes", ["slug"], unique=True)


def downgrade():
    op.drop_index("idx_fire_episodes_slug", table_name="fire_episodes")
    op.drop_column("fire_episodes", "seo_description")
    op.drop_column("fire_episodes", "seo_title")
    op.drop_column("fire_episodes", "slug")
