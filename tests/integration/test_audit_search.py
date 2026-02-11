from datetime import datetime, timedelta, timezone

from geoalchemy2 import WKTElement

from app.models.episode import FireEpisode
from app.models.region import ProtectedArea


def _create_episode(db_session, **kwargs):
    episode = FireEpisode(**kwargs)
    db_session.add(episode)
    db_session.commit()
    db_session.refresh(episode)
    return episode


def test_audit_search_by_province_returns_episodes(user_client, db_session):
    now = datetime.now(timezone.utc)
    _create_episode(
        db_session,
        status="closed",
        start_date=now - timedelta(days=30),
        end_date=now - timedelta(days=10),
        provinces=["Chubut"],
    )

    response = user_client.get("/api/v1/audit/search?q=Chubut&limit=5")
    assert response.status_code == 200
    payload = response.json()
    assert payload["resolved_place"]["type"] == "province"
    assert payload["episodes"]


def test_audit_search_by_protected_area_returns_episodes(user_client, db_session):
    area = ProtectedArea(
        official_name="Parque Nacional Test",
        category="national_park",
        boundary=WKTElement(
            "MULTIPOLYGON(((0 0, 1 0, 1 1, 0 1, 0 0)))", srid=4326
        ),
        jurisdiction="national",
        prohibition_years=60,
    )
    db_session.add(area)
    db_session.commit()
    db_session.refresh(area)

    now = datetime.now(timezone.utc)
    _create_episode(
        db_session,
        status="closed",
        start_date=now - timedelta(days=20),
        end_date=now - timedelta(days=5),
        bbox_minx=0,
        bbox_miny=0,
        bbox_maxx=1,
        bbox_maxy=1,
    )

    response = user_client.get("/api/v1/audit/search?q=Parque Nacional Test&limit=5")
    assert response.status_code == 200
    payload = response.json()
    assert payload["resolved_place"]["type"] == "protected_area"
    assert payload["episodes"]


def test_audit_search_no_match_returns_404(user_client, monkeypatch):
    from app.api.v1 import audit as audit_module

    monkeypatch.setattr(audit_module.GeocodingService, "geocode", lambda self, q: None)

    response = user_client.get("/api/v1/audit/search?q=NoMatch")
    assert response.status_code == 404
