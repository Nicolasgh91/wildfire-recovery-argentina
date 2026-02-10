from fastapi.testclient import TestClient

from app.main import app


def test_deprecation_headers():
    """
    Verify that Deprecation and Link headers are injected by middleware.
    """
    client = TestClient(app)
    response = client.get("/health")

    # Headers are case-insensitive in access but usually returned capitalized
    # TestClient/Starlette might normalise.

    assert response.status_code == 200

    # Check Deprecation Header
    # Standard: Deprecation: date="2026-04-30"
    dep_header = response.headers.get("deprecation")
    assert dep_header is not None, "Deprecation header missing"
    assert 'date="2026-04-30"' in dep_header

    # Check Link Header
    # Standard: Link: <https://docs.forestguard.ar/migration-guide>; rel="deprecation"
    link_header = response.headers.get("link")
    assert link_header is not None, "Link header missing"
    assert 'rel="deprecation"' in link_header
