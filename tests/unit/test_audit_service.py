from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from geoalchemy2.elements import WKTElement

from app.models.fire import FireEvent
from app.services.audit_service import AuditService


def test_audit_service_returns_fire(db_session):
    fire_id = uuid4()
    fire_date = datetime.now(timezone.utc) - timedelta(days=7)

    fire = FireEvent(
        id=fire_id,
        start_date=fire_date,
        end_date=fire_date + timedelta(days=1),
        total_detections=1,
        is_significant=True,
        province="Corrientes",
        centroid=WKTElement("POINT(-58.0 -28.0)", srid=4326),
    )
    db_session.add(fire)
    db_session.commit()

    service = AuditService(db_session)
    result = service.run_audit(lat=-28.0, lon=-58.0, radius_meters=500)

    assert result.fires_found >= 1
    fire_ids = {entry.fire_event_id for entry in result.fires}
    assert fire_id in fire_ids
    assert result.audit_hash
    assert result.evidence.thumbnails is not None


def test_audit_service_radius_cap(db_session):
    service = AuditService(db_session)
    with pytest.raises(ValueError):
        service.run_audit(lat=-28.0, lon=-58.0, radius_meters=100000)
