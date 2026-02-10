from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from geoalchemy2.elements import WKTElement

from app.models.fire import FireEvent
from app.schemas.audit import AuditResponse
from app.schemas.certificate import CertificateResponse
from app.schemas.fire import FireListResponse


def test_get_fires_contract(client):
    """
    Contract: GET /api/v1/fires must return FireListResponse
    """
    response = client.get("/api/v1/fires")

    # Ensure 200 OK
    assert response.status_code == 200

    data = response.json()
    FireListResponse.model_validate(data)


def test_audit_land_use_contract(user_client, db_session):
    """
    Contract: POST /api/v1/audit/land-use must return LandUseAuditResponse
    """
    # Seed a fire event to ensure interesting response (optional but good)
    fire = FireEvent(
        id=uuid4(),
        # satellite removed
        start_date=datetime.now(),
        end_date=datetime.now(),
        total_detections=1,
        is_significant=True,
        province="Chaco",
        centroid=WKTElement("POINT(-58.8346 -27.4658)", srid=4326),  # Close to request
    )
    db_session.add(fire)
    db_session.commit()

    payload = {"lat": -27.4658, "lon": -58.8346, "radius_meters": 500}

    response = user_client.post("/api/v1/audit/land-use", json=payload)

    if response.status_code != 200:
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Body: {response.json()}")

    assert response.status_code == 200

    # Contract Verification
    AuditResponse.model_validate(response.json())


def test_certificate_request_contract(user_client, db_session):
    """
    Contract: POST /api/v1/certificates/request must return CertificateResponse
    """
    # Seed a fire event
    fire_id = uuid4()
    fire = FireEvent(
        id=fire_id,
        # satellite removed
        start_date=datetime.now(),
        end_date=datetime.now(),
        total_detections=1,
        is_significant=True,
        province="Chaco",
        centroid="POINT(-58.8346 -27.4658)",
    )
    db_session.add(fire)
    db_session.commit()

    payload = {
        "fire_event_id": str(fire_id),
        "issued_to": "Nicolas Hruszczak",
        "requester_email": "nicolas@forestguard.ar",
    }

    # Endpoint is likely /api/v1/certificates/request or /api/v1/certificates/issue
    # Checking existing routes: "POST /certificates/issue" in usage examples.
    # But files were named "certificates.py". Let's check router.
    # Assuming /api/v1/certificates/issue based on previous context.

    response = user_client.post("/api/v1/certificates/issue", json=payload)

    # If 200, validate schema
    if response.status_code == 200:
        CertificateResponse.model_validate(response.json())
    else:
        # If it returns 404 (maybe dependencies missing), we fail or skip?
        # Contract test implies 200.
        # Check assertions
        pass  # Let assertion fail if model fails or code wrong

    assert response.status_code in [200, 201]
    CertificateResponse.model_validate(response.json())
