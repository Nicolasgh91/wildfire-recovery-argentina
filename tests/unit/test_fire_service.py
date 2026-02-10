from datetime import date, datetime, timezone
from uuid import uuid4

from app.models.fire import FireEvent
from app.services.fire_service import FireFilterParams, FireService


def _make_fire(**kwargs) -> FireEvent:
    defaults = {
        "id": uuid4(),
        "start_date": datetime.now(timezone.utc),
        "end_date": datetime.now(timezone.utc),
        "total_detections": 1,
        "avg_confidence": 80,
        "max_frp": 10,
        "estimated_area_hectares": 5,
        "province": "Test",
        "department": "Dept",
        "centroid": "POINT(0 0)",
    }
    defaults.update(kwargs)
    return FireEvent(**defaults)


def test_clamp_page_size_defaults(db_session):
    service = FireService(db_session)
    assert service.clamp_page_size(None) == 20
    assert service.clamp_page_size(0) == 1
    assert service.clamp_page_size(500) == 100


def test_search_filter_ilike(db_session):
    fire_a = _make_fire(province="Chaco")
    fire_b = _make_fire(province="Cordoba")
    db_session.add_all([fire_a, fire_b])
    db_session.commit()

    service = FireService(db_session)
    params = FireFilterParams(search="cha")
    filters = service.build_filter_conditions(params)
    results = db_session.query(FireEvent.id).filter(*filters).all()
    ids = {row[0] for row in results}

    assert fire_a.id in ids
    assert fire_b.id not in ids


def test_stats_ytd_comparison(db_session):
    today = date.today()
    current_year_date = datetime(today.year, 1, 1, tzinfo=timezone.utc)
    previous_year_date = datetime(today.year - 1, 1, 1, tzinfo=timezone.utc)

    fire_current = _make_fire(
        province="YTD",
        start_date=current_year_date,
        end_date=current_year_date,
    )
    fire_previous = _make_fire(
        province="YTD",
        start_date=previous_year_date,
        end_date=previous_year_date,
    )
    db_session.add_all([fire_current, fire_previous])
    db_session.commit()

    service = FireService(db_session)
    stats = service.get_stats(params=FireFilterParams(province=["YTD"]))

    assert stats.stats.total_fires >= 2
    assert stats.ytd_comparison is not None
    assert stats.ytd_comparison.total_fires.current >= 1
    assert stats.ytd_comparison.total_fires.previous >= 1
