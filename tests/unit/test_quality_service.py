from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.models.fire import FireDetection, FireEvent
from app.schemas.quality import QualityClass
from app.services.quality_service import DEFAULT_WEIGHTS, QualityService


def _make_fire(**kwargs) -> FireEvent:
    defaults = {
        "id": uuid4(),
        "start_date": datetime.now(timezone.utc),
        "end_date": datetime.now(timezone.utc),
        "total_detections": 1,
        "avg_confidence": 80,
        "province": "Test",
        "centroid": "POINT(0 0)",
    }
    defaults.update(kwargs)
    return FireEvent(**defaults)


def test_quality_score_high():
    score = QualityService._compute_reliability_score(
        confidence_score=80,
        imagery_score=100,
        climate_score=100,
        independent_score=100,
        weights=DEFAULT_WEIGHTS,
    )

    assert score == pytest.approx(92.0)
    assert QualityService._classify_score(score) == QualityClass.HIGH


def test_quality_limitations_missing_assets(db_session):
    has_func = db_session.execute(
        text("SELECT to_regprocedure('func_h3(numeric,numeric,integer)')")
    ).scalar()
    if not has_func:
        pytest.skip("func_h3 is not available in the test database")

    fire = _make_fire(avg_confidence=40)
    db_session.add(fire)

    detection = FireDetection(
        id=uuid4(),
        satellite="MODIS",
        instrument="test",
        detected_at=datetime.now(timezone.utc),
        location="POINT(0 0)",
        latitude=0,
        longitude=0,
        fire_event_id=fire.id,
    )
    db_session.add(detection)
    db_session.commit()

    service = QualityService(db_session)
    response = service.get_quality(fire.id)

    assert response is not None
    codes = {limitation.code for limitation in response.limitations}
    assert "no_imagery" in codes
    assert "no_climate" in codes


def test_quality_missing_event_returns_none(db_session):
    service = QualityService(db_session)
    assert service.get_quality(uuid4()) is None
