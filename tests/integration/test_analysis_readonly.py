import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.session import get_db
from app.main import app


def _resolve_prod_url() -> str | None:
    return os.getenv("PROD_DATABASE_URL") or settings.DATABASE_URL


@pytest.mark.skipif(
    os.getenv("RUN_PROD_READONLY_TESTS") != "1",
    reason="Set RUN_PROD_READONLY_TESTS=1 to enable production read-only smoke tests.",
)
def test_recurrence_readonly_smoke():
    url = _resolve_prod_url()
    if not url:
        pytest.skip("PROD_DATABASE_URL or DATABASE_URL not configured")

    engine = create_engine(url, pool_pre_ping=True)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        row = (
            session.execute(
                text(
                    """
                    SELECT ST_X(centroid::geometry) AS lon,
                           ST_Y(centroid::geometry) AS lat
                      FROM fire_events
                     WHERE centroid IS NOT NULL
                       AND h3_index IS NOT NULL
                     LIMIT 1
                    """
                )
            )
            .mappings()
            .first()
        )
        if not row:
            pytest.skip("No fire_events with centroid/h3_index in production DB")

        lon = float(row["lon"])
        lat = float(row["lat"])
        delta = 0.05

        def override_get_db():
            yield session

        app.dependency_overrides[get_db] = override_get_db

        client = TestClient(app)
        headers = {}
        if settings.API_KEY:
            headers["X-API-Key"] = settings.API_KEY.get_secret_value()

        response = client.get(
            "/api/v1/analysis/recurrence",
            params={
                "min_lon": lon - delta,
                "min_lat": lat - delta,
                "max_lon": lon + delta,
                "max_lat": lat + delta,
            },
            headers=headers,
        )

        if response.status_code == 403:
            pytest.skip("Missing or invalid API key for recurrence endpoint")

        assert response.status_code == 200
        payload = response.json()
        assert "cells" in payload
        assert "cell_count" in payload
    finally:
        app.dependency_overrides.clear()
        session.close()
        engine.dispose()
