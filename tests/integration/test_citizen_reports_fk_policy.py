"""
Integration checks for citizen_reports reporter_user_id FK policy.

Enforced policy:
    citizen_reports.reporter_user_id -> users(id) ON DELETE SET NULL
"""

import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text


@pytest.fixture(scope="module")
def db_engine():
    url = os.environ.get("DATABASE_URL") or os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("DATABASE_URL / TEST_DATABASE_URL not set - skipping integration tests")
    engine = create_engine(url)
    yield engine
    engine.dispose()


def _assert_target_schema_ready(conn) -> None:
    table_exists = conn.execute(
        text(
            """
            SELECT EXISTS (
              SELECT 1
              FROM information_schema.tables
              WHERE table_schema = 'public'
                AND table_name = 'citizen_reports'
            )
            """
        )
    ).scalar()
    assert table_exists, "citizen_reports table is required for FK policy enforcement"

    column_exists = conn.execute(
        text(
            """
            SELECT EXISTS (
              SELECT 1
              FROM information_schema.columns
              WHERE table_schema = 'public'
                AND table_name = 'citizen_reports'
                AND column_name = 'reporter_user_id'
            )
            """
        )
    ).scalar()
    assert column_exists, "citizen_reports.reporter_user_id column is required for FK policy enforcement"


def test_reporter_user_fk_is_set_null(db_engine):
    with db_engine.connect() as conn:
        _assert_target_schema_ready(conn)
        confdeltype = conn.execute(
            text(
                """
                SELECT c.confdeltype
                FROM pg_constraint c
                JOIN pg_class t ON t.oid = c.conrelid
                JOIN pg_namespace n ON n.oid = t.relnamespace
                JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(c.conkey)
                WHERE n.nspname = 'public'
                  AND t.relname = 'citizen_reports'
                  AND c.contype = 'f'
                  AND a.attname = 'reporter_user_id'
                LIMIT 1
                """
            )
        ).scalar()

    assert confdeltype == "n", (
        "reporter_user_id FK must use ON DELETE SET NULL "
        "(PostgreSQL confdeltype='n')"
    )


def test_delete_user_preserves_report_and_nulls_reporter_fk(db_engine):
    user_id = str(uuid4())
    report_id = f"FG-CIT-FK-{uuid4().hex[:8].upper()}"

    with db_engine.connect() as conn:
        _assert_target_schema_ready(conn)

        tx = conn.begin()
        try:
            conn.execute(
                text(
                    """
                    INSERT INTO users (
                      id, email, password_hash, full_name, role, is_verified
                    ) VALUES (
                      :user_id, :email, :password_hash, :full_name, 'user', true
                    )
                    """
                ),
                {
                    "user_id": user_id,
                    "email": f"fk-policy-{uuid4().hex[:8]}@example.com",
                    "password_hash": "integration-test-hash",
                    "full_name": "FK Policy Test",
                },
            )

            report_row_id = conn.execute(
                text(
                    """
                    INSERT INTO citizen_reports (
                      id,
                      report_id,
                      latitude,
                      longitude,
                      location,
                      report_type,
                      description,
                      observed_date,
                      reporter_email,
                      reporter_name,
                      reporter_user_id,
                      status,
                      related_fire_count,
                      related_protected_area_count,
                      created_at
                    ) VALUES (
                      gen_random_uuid(),
                      :report_id,
                      :lat,
                      :lon,
                      ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
                      'active_fire',
                      :description,
                      CURRENT_DATE,
                      'fk-policy@example.com',
                      'FK policy integration test',
                      :reporter_user_id,
                      'pending_review',
                      0,
                      0,
                      NOW()
                    )
                    RETURNING id
                    """
                ),
                {
                    "report_id": report_id,
                    "lat": -34.6037,
                    "lon": -58.3816,
                    "description": "Integration test to enforce ON DELETE SET NULL policy.",
                    "reporter_user_id": user_id,
                },
            ).scalar()

            conn.execute(
                text("DELETE FROM users WHERE id = :user_id"),
                {"user_id": user_id},
            )

            preserved_row = conn.execute(
                text(
                    """
                    SELECT reporter_user_id
                    FROM citizen_reports
                    WHERE id = :report_row_id
                    """
                ),
                {"report_row_id": str(report_row_id)},
            ).fetchone()

            assert preserved_row is not None, "Citizen report must be preserved after user delete"
            assert preserved_row[0] is None, "reporter_user_id must be NULL after user delete"
        finally:
            tx.rollback()

