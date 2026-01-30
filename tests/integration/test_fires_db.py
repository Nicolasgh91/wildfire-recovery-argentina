
import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from app.models.fire import FireEvent

def test_fires_filtering_integration(client, db_session):
    """
    Integration Test: Verify DB filtering for /fires endpoint.
    Scenario:
    1. Create 3 fires: 2 in Chaco, 1 in Corrientes.
    2. Filter by province=Chaco -> Expect 2.
    3. Filter by province=Corrientes -> Expect 1.
    """
    # 1. Setup Data
    fire_chaco_1 = FireEvent(
        id=uuid4(), start_date=datetime.now(), end_date=datetime.now(),
        total_detections=10, is_significant=True, province="Chaco",
        centroid="POINT(-60.0 -27.0)"
    )
    fire_chaco_2 = FireEvent(
        id=uuid4(), start_date=datetime.now(), end_date=datetime.now(),
        total_detections=5, is_significant=False, province="Chaco",
        centroid="POINT(-60.1 -27.1)"
    )
    fire_corrientes = FireEvent(
        id=uuid4(), start_date=datetime.now(), end_date=datetime.now(),
        total_detections=50, is_significant=True, province="Corrientes",
        centroid="POINT(-58.0 -28.0)"
    )
    
    db_session.add_all([fire_chaco_1, fire_chaco_2, fire_corrientes])
    db_session.commit()
    
    # 2. Test Chaco Filter
    response = client.get("/api/v1/fires?province=Chaco")
    assert response.status_code == 200
    data = response.json()
    # Note: DB might have other data, so we check if OUR fires are there, 
    # OR assume test DB is clean. 
    # With transaction rollback, it's clean-ish but might have seeded data.
    # Better to filter results by ID.
    ids = [item['id'] for item in data]
    assert str(fire_chaco_1.id) in ids
    assert str(fire_chaco_2.id) in ids
    assert str(fire_corrientes.id) not in ids

    # 3. Test Corrientes Filter
    response = client.get("/api/v1/fires?province=Corrientes")
    assert response.status_code == 200
    ids_corr = [item['id'] for item in response.json()]
    assert str(fire_corrientes.id) in ids_corr
    assert str(fire_chaco_1.id) not in ids_corr

def test_fires_pagination_integration(client, db_session):
    """
    Integration Test: Verify limit/offset.
    """
    # Create 15 fires
    fires = [
        FireEvent(
            id=uuid4(), start_date=datetime.now(), end_date=datetime.now(),
            total_detections=1, is_significant=False, province="TestProv",
            centroid="POINT(0 0)"
        ) for _ in range(15)
    ]
    db_session.add_all(fires)
    db_session.commit()
    
    # Page 1: Limit 10
    response = client.get("/api/v1/fires?limit=10&offset=0")
    assert len(response.json()) <= 10 # Could be less if DB small, but we added 15.
    # Actually if DB has pre-existing data, it might return more? No, limit applies.
    assert len(response.json()) == 10
    
    # Page 2: Limit 10, Offset 10
    response_p2 = client.get("/api/v1/fires?limit=10&offset=10")
    assert len(response_p2.json()) >= 5 # At least our remaining 5
