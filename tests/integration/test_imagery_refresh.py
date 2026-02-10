from datetime import datetime, timedelta, timezone
from uuid import uuid4

from geoalchemy2.elements import WKTElement

import app.services.imagery_service as imagery_service_module
from app.models.fire import FireEvent


def test_imagery_refresh_admin_success(admin_client, db_session, monkeypatch):
    fire_id = uuid4()
    fire_date = datetime.now(timezone.utc) - timedelta(days=3)

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

    def fake_refresh(self, fire_id_value, force_refresh=True):
        return {
            "fire_id": str(fire_id_value),
            "status": "updated",
            "image_id": "IMG-TEST",
            "slides_count": 3,
        }

    monkeypatch.setattr(
        imagery_service_module.ImageryService,
        "refresh_fire",
        fake_refresh,
    )

    response = admin_client.post(f"/api/v1/imagery/refresh/{fire_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "updated"
    assert data["image_id"] == "IMG-TEST"
    assert data["slides_count"] == 3
    assert data["fire_id"] == str(fire_id)


def test_imagery_refresh_requires_admin(user_client):
    fire_id = uuid4()
    response = user_client.post(f"/api/v1/imagery/refresh/{fire_id}")
    assert response.status_code == 403
