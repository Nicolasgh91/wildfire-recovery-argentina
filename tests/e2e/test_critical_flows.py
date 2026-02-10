import hashlib
import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from geoalchemy2.elements import WKTElement
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from app.api.routes import reports as reports_module
from app.core.config import settings
from app.main import app
from app.models.fire import FireEvent
from app.services.contact_service import ContactService


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
                "principal_id": "e2e-test",
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


def test_contact_flow_e2e(client, monkeypatch):
    async def _noop_send(self, message):
        return None

    monkeypatch.setattr(ContactService, "send_contact_email", _noop_send)

    payload = {
        "name": "E2E User",
        "email": "e2e@example.com",
        "subject": "Test",
        "message": "Hello from E2E",
    }
    attachment_content = b"hello-e2e"
    files = {
        "attachment": ("note.pdf", attachment_content, "application/pdf"),
    }

    response = client.post("/api/v1/contact", data=payload, files=files)
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "accepted"
    assert data["attachment"]["filename"] == "note.pdf"
    assert (
        data["attachment"]["sha256"] == hashlib.sha256(attachment_content).hexdigest()
    )


def test_dashboard_flow_e2e(user_client, db_session):
    if not settings.API_KEY:
        pytest.skip("API key not configured")

    department = f"E2E-{uuid4().hex}"
    now = datetime.now(timezone.utc)
    start_a = now - timedelta(days=2)
    start_b = now - timedelta(days=1)
    end_a = start_a + timedelta(hours=4)
    end_b = start_b + timedelta(hours=3)

    fire_a = FireEvent(
        id=uuid4(),
        centroid=WKTElement("POINT(-58.0 -28.0)", srid=4326),
        start_date=start_a,
        end_date=end_a,
        total_detections=5,
        avg_confidence=85,
        province="Corrientes",
        department=department,
        is_significant=True,
    )
    fire_b = FireEvent(
        id=uuid4(),
        centroid=WKTElement("POINT(-58.2 -28.2)", srid=4326),
        start_date=start_b,
        end_date=end_b,
        total_detections=3,
        avg_confidence=75,
        province="Misiones",
        department=department,
        is_significant=False,
    )
    db_session.add_all([fire_a, fire_b])
    db_session.commit()

    try:
        response_list = user_client.get(f"/api/v1/fires/?department={department}")
        assert response_list.status_code == 200
        payload_list = response_list.json()
        returned_ids = {f["id"] for f in payload_list["fires"]}
        assert str(fire_a.id) in returned_ids
        assert str(fire_b.id) in returned_ids

        response_stats = user_client.get(f"/api/v1/fires/stats?department={department}")
        assert response_stats.status_code == 200
        payload_stats = response_stats.json()
        assert payload_stats["stats"]["total_fires"] == 2

        response_export = user_client.get(
            f"/api/v1/fires/export?department={department}&format=csv"
        )
        assert response_export.status_code == 200
        assert "text/csv" in response_export.headers["content-type"]
        export_text = response_export.text
        assert str(fire_a.id) in export_text
        assert str(fire_b.id) in export_text
    finally:
        db_session.execute(
            text("DELETE FROM fire_events WHERE department = :department"),
            {"department": department},
        )
        db_session.commit()


def test_reports_verify_flow_e2e(db_engine, db_session):
    if not settings.API_KEY:
        pytest.skip("API key not configured")
    if not _audit_events_available(db_session):
        pytest.skip("audit_events table not available in test database")

    report_id = f"RPT-JUD-{uuid4().hex[:6].upper()}"
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
