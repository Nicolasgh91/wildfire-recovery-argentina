# SEO-S-03: tabla seo_region_thresholds con datos iniciales

"""Create seo_region_thresholds table and seed data

Revision ID: 005
Revises: 004
Create Date: 2026-03-10

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY, UUID

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "seo_region_thresholds",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("region_slug", sa.Text(), nullable=False),
        sa.Column("province_slugs", ARRAY(sa.Text()), nullable=False),
        sa.Column("min_affected_area_ha", sa.Integer(), nullable=False, server_default="500"),
        sa.Column("label", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("region_slug", name="uq_seo_region_thresholds_region_slug"),
    )
    op.execute("""
        INSERT INTO seo_region_thresholds (region_slug, province_slugs, min_affected_area_ha, label)
        VALUES
          ('patagonia',    ARRAY['neuquen','rio-negro','chubut','santa-cruz','tierra-del-fuego'], 800, 'Patagonia — baja densidad, umbrales altos'),
          ('cuyo',         ARRAY['mendoza','san-juan','san-luis'], 500, 'Cuyo — umbral estándar'),
          ('noa',          ARRAY['salta','jujuy','tucuman','catamarca','la-rioja'], 400, 'NOA — yungas y valles'),
          ('nea',          ARRAY['chaco','formosa','corrientes','misiones'], 300, 'NEA — gran chaco y selva misionera'),
          ('pampa-humeda', ARRAY['buenos-aires','santa-fe','entre-rios','la-pampa','cordoba'], 250, 'Pampa húmeda — alta densidad'),
          ('delta-parana', ARRAY['entre-rios','buenos-aires'], 150, 'Delta del Paraná — alto valor ecológico y mediático'),
          ('caba',         ARRAY['ciudad-autonoma-de-buenos-aires'], 50, 'CABA — máxima densidad urbana')
    """)


def downgrade():
    op.drop_table("seo_region_thresholds")
