"""
Integration checks for account soft-delete policy.

Expected behavior:
  - users row is retained with is_deleted = true
  - citizen_reports is preserved
  - reporter_user_id is nulled for deleted users
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


def test_soft_delete_preserves_reports_and_nullifies_reporter(db_engine):
    user_id = str(uuid4())
    report_id = f"FG-CIT-SOFT-{uuid4().hex[:8].upper()}"

    with db_engine.connect() as conn:
        has_soft_delete_columns = conn.execute(
            text(
                """
                SELECT
                  EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_schema='public' AND table_name='users' AND column_name='is_deleted'
                  )
                  AND EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_schema='public' AND table_name='users' AND column_name='deleted_at'
                  )
                """
            )
        ).scalar()
        assert has_soft_delete_columns, "users soft-delete columns are required"

        tx = conn.begin()
        try:
            conn.execute(
                text(
                    """
                    INSERT INTO users (
                      id, email, password_hash, full_name, role, is_verified, is_deleted
                    ) VALUES (
                      :user_id, :email, :password_hash, :full_name, 'user', true, false
                    )
                    """
                ),
                {
                    "user_id": user_id,
                    "email": f"soft-delete-{uuid4().hex[:8]}@example.com",
                    "password_hash": "integration-test-hash",
                    "full_name": "Soft Delete Test",
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
                      'soft-delete@example.com',
                      'Soft delete integration test',
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
                    "description": "Integration test for account soft delete policy.",
                    "reporter_user_id": user_id,
                },
            ).scalar()

            conn.execute(
                text(
                    """
                    UPDATE users
                    SET is_deleted = true,
                        deleted_at = NOW(),
                        deletion_reason = 'integration_test'
                    WHERE id = :user_id
                    """
                ),
                {"user_id": user_id},
            )

            conn.execute(
                text(
                    """
                    UPDATE citizen_reports
                    SET reporter_user_id = NULL
                    WHERE reporter_user_id = :user_id
                    """
                ),
                {"user_id": user_id},
            )

            user_row = conn.execute(
                text(
                    """
                    SELECT is_deleted, deleted_at
                    FROM users
                    WHERE id = :user_id
                    """
                ),
                {"user_id": user_id},
            ).fetchone()
            assert user_row is not None
            assert user_row[0] is True
            assert user_row[1] is not None

            report_row = conn.execute(
                text(
                    """
                    SELECT reporter_user_id
                    FROM citizen_reports
                    WHERE id = :report_row_id
                    """
                ),
                {"report_row_id": str(report_row_id)},
            ).fetchone()
            assert report_row is not None
            assert report_row[0] is None
        finally:
            tx.rollback()
