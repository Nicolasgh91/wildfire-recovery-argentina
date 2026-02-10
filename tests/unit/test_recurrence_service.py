from datetime import datetime, timezone
from uuid import uuid4

from geoalchemy2 import WKTElement

from app.models.fire import FireEvent
from app.services.recurrence_service import BBox, RecurrenceService


def _make_fire(**kwargs) -> FireEvent:
    defaults = {
        "id": uuid4(),
        "start_date": datetime.now(timezone.utc),
        "end_date": datetime.now(timezone.utc),
        "total_detections": 1,
        "avg_confidence": 80,
        "province": "Test",
        "centroid": WKTElement("POINT(0 0)", srid=4326),
        "h3_index": 617733123456789,
    }
    defaults.update(kwargs)
    return FireEvent(**defaults)


def test_recurrence_returns_cells(db_session):
    fire_a = _make_fire()
    fire_b = _make_fire(id=uuid4())
    db_session.add_all([fire_a, fire_b])
    db_session.commit()

    service = RecurrenceService(db_session)
    response = service.get_recurrence(
        BBox(min_lon=-1, min_lat=-1, max_lon=1, max_lat=1)
    )

    assert response.cell_count >= 1
    assert response.cells
    assert 0 <= response.max_intensity <= 1
    assert response.cells[0].h3
