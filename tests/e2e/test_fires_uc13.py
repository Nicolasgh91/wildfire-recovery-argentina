"""
Tests para Fire Events API - ForestGuard UC-13.

Simplified tests that work with existing DB data to avoid geography seeding issues.
"""

import pytest
from datetime import datetime

# =============================================================================
# BASIC ENDPOINT TESTS (No fixture seeding - uses existing DB data)
# =============================================================================

def test_list_fires_returns_200(client):
    """Endpoint /fires returns 200 with correct structure."""
    response = client.get("/api/v1/fires")
    assert response.status_code == 200
    data = response.json()
    
    # Verify structure
    assert "fires" in data
    assert "pagination" in data
    assert "filters_applied" in data
    
    # Pagination structure
    assert "total" in data["pagination"]
    assert "page" in data["pagination"]
    assert "page_size" in data["pagination"]

def test_list_fires_pagination(client):
    """Pagination works correctly."""
    response = client.get("/api/v1/fires?page=1&page_size=5")
    assert response.status_code == 200
    data = response.json()
    
    assert data["pagination"]["page"] == 1
    assert data["pagination"]["page_size"] == 5
    assert len(data["fires"]) <= 5

def test_list_fires_filter_province(client):
    """Filter by province returns 200."""
    response = client.get("/api/v1/fires?province=Corrientes")
    assert response.status_code == 200
    data = response.json()
    
    # All returned fires should be from Corrientes (if any)
    for fire in data["fires"]:
        assert fire["province"] == "Corrientes"

def test_list_fires_filter_date_range(client):
    """Filter by date range returns 200."""
    response = client.get("/api/v1/fires?date_from=2020-01-01&date_to=2024-12-31")
    assert response.status_code == 200
    data = response.json()
    
    # Verify dates are within range
    for fire in data["fires"]:
        start_date = datetime.fromisoformat(fire["start_date"].replace("Z", "+00:00"))
        assert start_date.year >= 2020
        assert start_date.year <= 2024

def test_list_fires_sorting_desc(client):
    """Sorting by date descending works."""
    response = client.get("/api/v1/fires?sort_by=start_date&sort_desc=true&page_size=10")
    assert response.status_code == 200
    data = response.json()
    
    if len(data["fires"]) >= 2:
        dates = [f["start_date"] for f in data["fires"]]
        # First should be >= second (descending)
        assert dates[0] >= dates[1]

def test_list_fires_sorting_asc(client):
    """Sorting by date ascending works."""
    response = client.get("/api/v1/fires?sort_by=start_date&sort_desc=false&page_size=10")
    assert response.status_code == 200
    data = response.json()
    
    if len(data["fires"]) >= 2:
        dates = [f["start_date"] for f in data["fires"]]
        # First should be <= second (ascending)
        assert dates[0] <= dates[1]

def test_export_csv(client):
    """Export to CSV returns proper content-type."""
    response = client.get("/api/v1/fires/export?format=csv")
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    
    content = response.text
    assert "id,start_date" in content

def test_stats_endpoint(client):
    """Stats endpoint returns 200 with correct structure."""
    response = client.get("/api/v1/fires/stats")
    assert response.status_code == 200
    data = response.json()
    
    assert "stats" in data
    assert "period" in data
    assert "total_fires" in data["stats"]

def test_provinces_list(client):
    """Provinces endpoint returns list."""
    response = client.get("/api/v1/fires/provinces")
    assert response.status_code == 200
    data = response.json()
    
    assert "provinces" in data
    assert "total" in data
    
    if data["total"] > 0:
        assert "name" in data["provinces"][0]
        assert "fire_count" in data["provinces"][0]

def test_fire_detail_not_found(client):
    """Non-existent fire returns 404."""
    response = client.get("/api/v1/fires/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404

def test_fire_detail_invalid_uuid(client):
    """Invalid UUID returns 422."""
    response = client.get("/api/v1/fires/not-a-uuid")
    assert response.status_code == 422
