"""Tests for page_size cap on /fires endpoint (BL-005 / PERF-001)."""
import pytest

from app.main import app

import fastapi.testclient as _tc


@pytest.fixture()
def client():
    with _tc.TestClient(app) as c:
        yield c


class TestFiresPagination:
    def test_page_size_too_large_returns_422(self, client):
        resp = client.get("/api/v1/fires", params={"page_size": 999})
        assert resp.status_code == 422

    def test_page_size_zero_returns_422(self, client):
        resp = client.get("/api/v1/fires", params={"page_size": 0})
        assert resp.status_code == 422

    def test_page_size_negative_returns_422(self, client):
        resp = client.get("/api/v1/fires", params={"page_size": -1})
        assert resp.status_code == 422

    def test_page_size_200_accepted(self, client):
        resp = client.get("/api/v1/fires", params={"page_size": 200})
        # May fail with 500 if DB is not available, but should NOT be 422
        assert resp.status_code != 422

    def test_page_size_50_accepted(self, client):
        resp = client.get("/api/v1/fires", params={"page_size": 50})
        assert resp.status_code != 422
