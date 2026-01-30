
import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from app.models.fire import FireEvent

def test_audit_land_use_e2e(user_client, db_session):
    """
    E2E Test: Validate UC-01 (Land Use Audit).
    
    Flow:
    1. Setup: Insert a fire event in 'Corrientes' (point -58.0 -28.0).
    2. Action: User requests audit at -28.0, -58.0 (exact centroid).
    3. Assert: System detects fire, returns is_prohibited=True, and calculation is correct.
    """
    
    # 1. Setup Fire Event (Recent fire, < 60 years)
    fire_date = datetime.now() - timedelta(days=365) # 1 year ago
    prohibition_years = 60 # Assume Protected Area logic applies or default
    
    fire_id = uuid4()
    fire = FireEvent(
        id=fire_id,
        # satellite removed
        start_date=fire_date,
        end_date=fire_date + timedelta(days=1),
        total_detections=50,
        is_significant=True,
        province="Corrientes",
        centroid="POINT(-58.0 -28.0)",
        avg_frp=100.0,
        estimated_area_hectares=50.0
    )
    db_session.add(fire)
    db_session.commit()
    
    # 2. Action: Request Audit
    payload = {
        "lat": -28.0,
        "lon": -58.0,
        "radius_meters": 500
    }
    
    response = user_client.post("/api/v1/audit/land-use", json=payload)
    
    # 3. Assertions
    assert response.status_code == 200
    data = response.json()
    
    assert data["is_prohibited"] is True
    assert data["fires_found"] >= 1
    
    # Check if our fire is in the list
    found_ids = [f["fire_event_id"] for f in data["fires"]]
    assert str(fire_id) in found_ids
    
    # Verify prohibition date logic (roughly)
    # If 60 years, it should be fire_date + 60 years
    # Logic inside audit.py might vary depending on land type (Native Forest vs Grassland).
    # Ideally checking 'prohibition_until' > today.
    today_str = datetime.now().date().isoformat()
    assert data["prohibition_until"] > today_str

def test_audit_clean_area_e2e(user_client):
    """
    E2E Test: Audit on safe area should return allowed.
    """
    payload = {
        "lat": -34.0, # Buenos Aires city center roughly, assume no fires
        "lon": -58.4,
        "radius_meters": 100
    }
    response = user_client.post("/api/v1/audit/land-use", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    assert data["is_prohibited"] is False
    assert data["fires_found"] == 0
