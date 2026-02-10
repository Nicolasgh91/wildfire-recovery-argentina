from datetime import datetime, timedelta, timezone
from uuid import uuid4

from geoalchemy2.elements import WKTElement

from app.models.fire import FireEvent


def test_audit_land_use_integration(user_client, db_session):
    fire_id = uuid4()
    fire_date = datetime.now(timezone.utc) - timedelta(days=30)

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

    payload = {"lat": -28.0, "lon": -58.0, "radius_meters": 500}
    response = user_client.post("/api/v1/audit/land-use", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["fires_found"] >= 1
    fire_ids = [item["fire_event_id"] for item in data.get("fires", [])]
    assert str(fire_id) in fire_ids
    assert data.get("audit_hash")
