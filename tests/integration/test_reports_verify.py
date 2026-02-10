import json
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from app.api.routes import reports as reports_module
from app.core.config import settings
from app.main import app


def _insert_audit_event(db_engine, report_id: str, verification_hash: str) -> None:
    details = {
        "report_id": report_id,
        "verification_hash": verification_hash,
    }
    with db_engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO audit_events (
                    principal_id,
                    principal_role,
                    action,
                    resource_type,
                    resource_id,
                    details
                ) VALUES (
                    :principal_id,
                    :principal_role,
                    :action,
                    :resource_type,
                    :resource_id,
                    CAST(:details AS JSONB)
                )
                """
            ),
            {
                "principal_id": "test-key",
                "principal_role": "api_key",
                "action": "report_generated",
                "resource_type": "fire_event",
                "resource_id": str(uuid4()),
                "details": json.dumps(details),
            },
        )


def _delete_audit_event(db_engine, report_id: str) -> None:
    with db_engine.begin() as conn:
        conn.execute(
            text(
                """
                DELETE FROM audit_events
                 WHERE action = 'report_generated'
                   AND details::jsonb->>'report_id' = :report_id
                """
            ),
            {"report_id": report_id},
        )


def _client_with_engine(db_engine) -> TestClient:
    Session = sessionmaker(bind=db_engine)

    def _override_get_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[reports_module.get_db] = _override_get_db
    return TestClient(app)


def _audit_events_available(db_session) -> bool:
    row = db_session.execute(text("SELECT to_regclass('public.audit_events')")).scalar()
    return row is not None


def test_reports_verify_uses_audit_events(db_engine, db_session):
    if not _audit_events_available(db_session):
        pytest.skip("audit_events table not available in test database")
    if not settings.API_KEY:
        pytest.skip("API key not configured")

    report_id = "RPT-JUD-20260203-VERIFY01"
    verification_hash = "sha256:" + ("c" * 64)
    _insert_audit_event(db_engine, report_id, verification_hash)

    try:
        with _client_with_engine(db_engine) as client:
            response = client.get(
                f"/api/v1/reports/{report_id}/verify",
                params={"hash_to_verify": verification_hash},
                headers={"X-API-Key": settings.API_KEY.get_secret_value()},
            )
    finally:
        _delete_audit_event(db_engine, report_id)
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["is_valid"] is True
    assert payload["report_id"] == report_id


def test_reports_verify_detects_mismatch(db_engine, db_session):
    if not _audit_events_available(db_session):
        pytest.skip("audit_events table not available in test database")
    if not settings.API_KEY:
        pytest.skip("API key not configured")

    report_id = "RPT-JUD-20260203-VERIFY02"
    verification_hash = "sha256:" + ("d" * 64)
    _insert_audit_event(db_engine, report_id, verification_hash)

    try:
        with _client_with_engine(db_engine) as client:
            response = client.get(
                f"/api/v1/reports/{report_id}/verify",
                params={"hash_to_verify": "sha256:" + ("e" * 64)},
                headers={"X-API-Key": settings.API_KEY.get_secret_value()},
            )
    finally:
        _delete_audit_event(db_engine, report_id)
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["is_valid"] is False
    assert payload["report_id"] == report_id


def test_reports_verify_404_when_missing(db_engine, db_session):
    if not settings.API_KEY:
        pytest.skip("API key not configured")

    with _client_with_engine(db_engine) as client:
        response = client.get(
            "/api/v1/reports/RPT-JUD-UNKNOWN/verify",
            params={"hash_to_verify": "sha256:" + ("f" * 64)},
            headers={"X-API-Key": settings.API_KEY.get_secret_value()},
        )
    app.dependency_overrides.clear()
    assert response.status_code == 404
