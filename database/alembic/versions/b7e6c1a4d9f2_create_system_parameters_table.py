"""create_system_parameters_table

Revision ID: b7e6c1a4d9f2
Revises: 4c8d7e1a2b3c
Create Date: 2026-02-02 18:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "b7e6c1a4d9f2"
down_revision: Union[str, None] = "4c8d7e1a2b3c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "system_parameters",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("param_key", sa.String(length=50), nullable=False),
        sa.Column("param_value", postgresql.JSONB(), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column(
            "category",
            sa.String(length=30),
            server_default=sa.text("'general'"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.Column(
            "previous_values",
            postgresql.JSONB(),
            server_default=sa.text("'[]'::jsonb"),
            nullable=True,
        ),
        sa.CheckConstraint(
            "category IN ("
            "'general', 'audit', 'imagery', 'reports', "
            "'clustering', 'notifications', 'limits'"
            ")",
            name="system_parameters_category_check",
        ),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("param_key"),
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION track_parameter_changes()
        RETURNS TRIGGER AS $$
        BEGIN
            IF OLD.param_value IS DISTINCT FROM NEW.param_value THEN
                NEW.previous_values = COALESCE(OLD.previous_values, '[]'::jsonb)
                    || jsonb_build_array(jsonb_build_object(
                        'value', OLD.param_value,
                        'changed_at', OLD.updated_at,
                        'changed_by', OLD.updated_by
                    ));
                NEW.updated_at = NOW();
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    op.execute(
        """
        CREATE TRIGGER trg_track_parameter_changes
        BEFORE UPDATE ON system_parameters
        FOR EACH ROW EXECUTE FUNCTION track_parameter_changes();
        """
    )

    op.execute(
        """
        INSERT INTO system_parameters (param_key, param_value, description, category) VALUES
        ('audit_search_radius_default',
         '{"value": 500, "unit": "meters"}',
         'Default search radius for land use audits',
         'audit'),

        ('audit_search_radius_max',
         '{"value": 5000, "unit": "meters", "is_hard_cap": true}',
         'Max allowed search radius (hard cap)',
         'audit'),

        ('carousel_batch_size',
         '{"value": 15}',
         'Number of fires processed per carousel batch',
         'imagery'),

        ('cloud_coverage_thresholds',
         '{"initial": 10, "increments": [20, 30, 50], "max": 50}',
         'Adaptive cloud thresholds for imagery selection',
         'imagery'),

        ('carousel_priority_weights',
         '{"proximity_pa": 0.40, "frp": 0.30, "area": 0.20, "recurrence": 0.10}',
         'Weights for carousel priority scoring',
         'imagery'),

        ('closure_report_min_area_ha',
         '{"value": 10}',
         'Minimum area (ha) for auto-generating closure reports',
         'reports'),

        ('closure_report_max_retry_days',
         '{"value": 30}',
         'Max retry days before marking closure report incomplete',
         'reports'),

        ('closure_report_cloud_max',
         '{"value": 40, "with_cloud_masking": true}',
         'Max cloud threshold with cloud masking enabled',
         'reports'),

        ('dashboard_page_size_default',
         '{"value": 20}',
         'Default page size for listings',
         'limits'),

        ('dashboard_page_size_max',
         '{"value": 100, "is_hard_cap": true}',
         'Max page size (hard cap for DoS protection)',
         'limits'),

        ('h3_max_cells_per_query',
         '{"value": 5000, "is_hard_cap": true}',
         'Max H3 cells per query (DoS protection)',
         'limits'),

        ('report_max_images',
         '{"value": 12, "is_fixed": true}',
         'Fixed number of images per historical report',
         'reports'),

        ('report_image_cost_usd',
         '{"value": 0.50}',
         'USD cost per HD image in reports',
         'reports');
        """
    )

    op.execute(
        "COMMENT ON TABLE system_parameters IS "
        "'Admin-managed configuration parameters. Values with is_hard_cap=true "
        "cannot be exceeded by any endpoint.'"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_track_parameter_changes ON system_parameters;")
    op.execute("DROP FUNCTION IF EXISTS track_parameter_changes();")
    op.drop_table("system_parameters")
