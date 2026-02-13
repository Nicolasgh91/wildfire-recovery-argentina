"""fg_ep_22_insert_canonical_system_parameters

Revision ID: 7196f62a30d4
Revises: dcdc9d71a209
Create Date: 2026-02-13 18:41:42.114990

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '7196f62a30d4'
down_revision: Union[str, None] = 'dcdc9d71a209'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
          IF EXISTS (
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name = 'system_parameters'
          ) THEN
            INSERT INTO public.system_parameters (
              param_key, param_value, description, category
            )
            VALUES
              (
                'event_spatial_epsilon_meters',
                '{"value": 2000, "unit": "meters"}'::jsonb,
                'Canonical spatial epsilon for event clustering',
                'clustering'
              ),
              (
                'event_temporal_window_hours',
                '{"value": 48, "unit": "hours"}'::jsonb,
                'Canonical temporal window for event clustering',
                'clustering'
              ),
              (
                'event_monitoring_window_hours',
                '{"value": 168, "unit": "hours"}'::jsonb,
                'Canonical monitoring window for event recency',
                'clustering'
              ),
              (
                'episode_spatial_epsilon_meters',
                '{"value": 6000, "unit": "meters"}'::jsonb,
                'Canonical spatial epsilon for episode grouping',
                'clustering'
              ),
              (
                'episode_temporal_window_hours',
                '{"value": 96, "unit": "hours"}'::jsonb,
                'Canonical temporal window for episode grouping',
                'clustering'
              )
            ON CONFLICT (param_key) DO NOTHING;
          END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
          IF EXISTS (
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name = 'system_parameters'
          ) THEN
            DELETE FROM public.system_parameters
            WHERE param_key IN (
              'event_spatial_epsilon_meters',
              'event_temporal_window_hours',
              'event_monitoring_window_hours',
              'episode_spatial_epsilon_meters',
              'episode_temporal_window_hours'
            );
          END IF;
        END $$;
        """
    )
