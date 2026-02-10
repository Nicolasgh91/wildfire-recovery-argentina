from datetime import datetime, timezone
from uuid import uuid4

from geoalchemy2 import WKTElement

from app.models.fire import FireEvent


def _make_fire(**overrides) -> FireEvent:
    """
    Helper to build FireEvent rows for tests.
    Uses WKTElement with SRID=4326 to satisfy Geography column requirements.
    """
    now = datetime.now(timezone.utc)
    payload = {
        "id": uuid4(),
        "start_date": now,
        "end_date": now,
        "total_detections": 1,
        "is_significant": False,
        "province": "Test",
        "centroid": WKTElement("POINT(-60.0 -27.0)", srid=4326),
    }
    payload.update(overrides)
    return FireEvent(**payload)


def test_fires_filtering_integration(user_client, db_session):
    """
    Integration Test: Verify DB filtering for /fires endpoint.
    Scenario:
    1. Create 3 fires: 2 in Chaco, 1 in Corrientes.
    2. Filter by province=Chaco -> Expect 2.
    3. Filter by province=Corrientes -> Expect 1.

    Notes:
    - /api/v1/fires requires authentication (API key or JWT).
    - centroid must be a Geography-compatible value (use WKTElement with SRID 4326).
    - Response shape is {fires: [...], pagination: {...}}.
    - TEST_DATABASE_URL must point to a PostGIS-enabled database.
    """
    # 1. Setup Data
    fire_chaco_1 = _make_fire(
        total_detections=10,
        is_significant=True,
        province="Chaco",
        centroid=WKTElement("POINT(-60.0 -27.0)", srid=4326),
    )
    fire_chaco_2 = _make_fire(
        total_detections=5,
        is_significant=False,
        province="Chaco",
        centroid=WKTElement("POINT(-60.1 -27.1)", srid=4326),
    )
    fire_corrientes = _make_fire(
        total_detections=50,
        is_significant=True,
        province="Corrientes",
        centroid=WKTElement("POINT(-58.0 -28.0)", srid=4326),
    )

    db_session.add_all([fire_chaco_1, fire_chaco_2, fire_corrientes])
    db_session.commit()

    # 2. Test Chaco Filter
    response = user_client.get("/api/v1/fires?province=Chaco")
    assert response.status_code == 200
    data = response.json()
    ids = [item["id"] for item in data.get("fires", [])]
    assert str(fire_chaco_1.id) in ids
    assert str(fire_chaco_2.id) in ids
    assert str(fire_corrientes.id) not in ids

    # 3. Test Corrientes Filter
    response = user_client.get("/api/v1/fires?province=Corrientes")
    assert response.status_code == 200
    ids_corr = [item["id"] for item in response.json().get("fires", [])]
    assert str(fire_corrientes.id) in ids_corr
    assert str(fire_chaco_1.id) not in ids_corr


def test_fires_pagination_integration(user_client, db_session):
    """
    Integration Test: Verify limit/offset.
    """
    # Create 15 fires
    fires = [
        _make_fire(province="TestProv", centroid=WKTElement("POINT(0 0)", srid=4326))
        for _ in range(15)
    ]
    db_session.add_all(fires)
    db_session.commit()

    # Page 1: Limit 10
    response = user_client.get("/api/v1/fires?page=1&page_size=10")
    payload = response.json()
    assert len(payload.get("fires", [])) <= 10
    assert len(payload.get("fires", [])) == 10

    # Page 2: Limit 10, Offset 10
    response_p2 = user_client.get("/api/v1/fires?page=2&page_size=10")
    payload_p2 = response_p2.json()
    assert len(payload_p2.get("fires", [])) >= 5
