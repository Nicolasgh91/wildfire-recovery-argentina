"""create_user_saved_filters_table

Revision ID: f2a1c4d7e6b5
Revises: e4a1d7c9b2f0
Create Date: 2026-02-02 19:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "f2a1c4d7e6b5"
down_revision: Union[str, None] = "e4a1d7c9b2f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_saved_filters",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("filter_name", sa.String(length=100), nullable=False),
        sa.Column("filter_config", postgresql.JSONB(), nullable=False),
        sa.Column("is_default", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("last_used_at", sa.DateTime(timezone=True)),
        sa.Column("use_count", sa.Integer(), server_default=sa.text("0")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "filter_name"),
    )

    op.create_index(
        "idx_user_filters_single_default",
        "user_saved_filters",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("is_default = true"),
    )
    op.execute(
        "CREATE INDEX idx_user_filters_user "
        "ON user_saved_filters (user_id, last_used_at DESC);"
    )

    op.execute("ALTER TABLE user_saved_filters ENABLE ROW LEVEL SECURITY;")
    op.execute(
        "CREATE POLICY user_filters_select ON user_saved_filters "
        "FOR SELECT USING (user_id = auth.uid());"
    )
    op.execute(
        "CREATE POLICY user_filters_insert ON user_saved_filters "
        "FOR INSERT WITH CHECK (user_id = auth.uid());"
    )
    op.execute(
        "CREATE POLICY user_filters_update ON user_saved_filters "
        "FOR UPDATE USING (user_id = auth.uid());"
    )
    op.execute(
        "CREATE POLICY user_filters_delete ON user_saved_filters "
        "FOR DELETE USING (user_id = auth.uid());"
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION update_filter_usage(p_filter_id UUID)
        RETURNS void AS $$
        BEGIN
            UPDATE user_saved_filters
            SET last_used_at = NOW(),
                use_count = use_count + 1
            WHERE id = p_filter_id;
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;
        """
    )

    op.execute(
        "COMMENT ON TABLE user_saved_filters IS "
        "'Saved filters per user for the fire dashboard. "
        "filter_config example: {\"province\": \"Cordoba\", \"status\": [\"active\"], "
        "\"date_from\": \"2025-01-01\", \"date_to\": \"2025-12-31\", \"min_area_ha\": 10}';"
    )


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS update_filter_usage(UUID);")
    op.execute("DROP POLICY IF EXISTS user_filters_delete ON user_saved_filters;")
    op.execute("DROP POLICY IF EXISTS user_filters_update ON user_saved_filters;")
    op.execute("DROP POLICY IF EXISTS user_filters_insert ON user_saved_filters;")
    op.execute("DROP POLICY IF EXISTS user_filters_select ON user_saved_filters;")
    op.execute("DROP INDEX IF EXISTS idx_user_filters_user;")
    op.drop_index("idx_user_filters_single_default", table_name="user_saved_filters")
    op.drop_table("user_saved_filters")
