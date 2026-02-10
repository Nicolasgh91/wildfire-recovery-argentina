"""extend_satellite_images_for_reproducibility

Revision ID: e4a1d7c9b2f0
Revises: c3e2f9a1b8d0
Create Date: 2026-02-02 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "e4a1d7c9b2f0"
down_revision: Union[str, None] = "c3e2f9a1b8d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "satellite_images",
        sa.Column("gee_system_index", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "satellite_images",
        sa.Column("visualization_params", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "satellite_images",
        sa.Column(
            "is_reproducible",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=True,
        ),
    )

    op.create_index(
        "idx_satellite_images_reproducible",
        "satellite_images",
        ["is_reproducible"],
        unique=False,
        postgresql_where=sa.text("is_reproducible = true"),
    )
    op.create_index(
        "idx_satellite_images_gee_index",
        "satellite_images",
        ["gee_system_index"],
        unique=False,
        postgresql_where=sa.text("gee_system_index IS NOT NULL"),
    )

    op.execute(
        "COMMENT ON COLUMN satellite_images.gee_system_index IS "
        "'Unique image identifier in Google Earth Engine (system:index). "
        "Allows retrieving the exact original image.'"
    )
    op.execute(
        "COMMENT ON COLUMN satellite_images.visualization_params IS "
        "'Visualization parameters for exact reproducibility. "
        "Expected structure: {\"bands\": [...], \"min\": [...], \"max\": [...], "
        "\"gamma\": [...], \"gain\": 1.0, \"bias\": 0.0}.'"
    )
    op.execute(
        "COMMENT ON COLUMN satellite_images.is_reproducible IS "
        "'True when the image has all metadata required to reproduce the visualization.'"
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION validate_visualization_params()
        RETURNS TRIGGER AS $$
        BEGIN
            IF NEW.visualization_params IS NOT NULL THEN
                IF NOT (
                    NEW.visualization_params ? 'bands' AND
                    NEW.visualization_params ? 'min' AND
                    NEW.visualization_params ? 'max'
                ) THEN
                    RAISE EXCEPTION 'visualization_params must include bands, min, and max';
                END IF;

                IF (
                    NEW.gee_system_index IS NOT NULL AND
                    NEW.visualization_params ? 'bands' AND
                    NEW.visualization_params ? 'min' AND
                    NEW.visualization_params ? 'max'
                ) THEN
                    NEW.is_reproducible = true;
                END IF;
            END IF;

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    op.execute(
        """
        CREATE TRIGGER trg_validate_viz_params
        BEFORE INSERT OR UPDATE ON satellite_images
        FOR EACH ROW EXECUTE FUNCTION validate_visualization_params();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_validate_viz_params ON satellite_images;")
    op.execute("DROP FUNCTION IF EXISTS validate_visualization_params();")
    op.drop_index("idx_satellite_images_gee_index", table_name="satellite_images")
    op.drop_index("idx_satellite_images_reproducible", table_name="satellite_images")
    op.drop_column("satellite_images", "is_reproducible")
    op.drop_column("satellite_images", "visualization_params")
    op.drop_column("satellite_images", "gee_system_index")
