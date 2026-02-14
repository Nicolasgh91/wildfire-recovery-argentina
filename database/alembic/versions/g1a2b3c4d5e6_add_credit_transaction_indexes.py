"""Add composite index on credit_transactions (user_id, created_at DESC)

Revision ID: g1a2b3c4d5e6
Revises: f2a1c4d7e6b5
Create Date: 2026-02-14

BL-006 / PERF-002: Optimise paginated transaction queries.
Uses CREATE INDEX CONCURRENTLY to avoid locking the table.
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "g1a2b3c4d5e6"
down_revision = "f2a1c4d7e6b5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # CREATE INDEX CONCURRENTLY cannot run inside a transaction block.
    op.execute(
        "COMMIT"
    )
    op.execute(
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS "
        "ix_credit_transactions_user_created "
        "ON credit_transactions (user_id, created_at DESC)"
    )


def downgrade() -> None:
    op.execute(
        "COMMIT"
    )
    op.execute(
        "DROP INDEX CONCURRENTLY IF EXISTS ix_credit_transactions_user_created"
    )
