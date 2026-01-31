"""
Tests para Fire Events API - ForestGuard UC-13.

Tests unitarios y de integración para:
- GET /fires (listado con filtros)
- GET /fires/{id} (detalle)
- GET /fires/export (exportación)
- GET /fires/stats (estadísticas)
- GET /fires/provinces (dropdown)

Autor: ForestGuard Dev Team
"""

import pytest
from datetime import date, datetime, timedelta
from uuid import UUID
from fastapi.testclient import TestClient
from fastapi import FastAPI

# Import modules to test
from schemas_fire import (
    FireEventListItem,
    FireListResponse,
    PaginationMeta,
    Coordinates,
    SortField,
    ExportFormat,
    FireStatus,
)
from routes_fires import router, MOCK_FIRES


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def app():
    """Create FastAPI app for testing."""
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    return app

@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


# =============================================================================
# SCHEMA TESTS
# =============================================================================

class TestCoordinates:
    """Tests para Coordinates schema."""
    
    def test_valid_coordinates(self):
        """Coordenadas válidas."""
        coords = Coordinates(latitude=-27.4658, longitude=-58.8346)
        assert coords.latitude == -27.4658
        assert coords.longitude == -58.8346
    
    def test_boundary_values(self):
        """Valores límite."""
        coords = Coordinates(latitude=-90, longitude=-180)
        assert coords.latitude == -90
        assert coords.longitude == -180
        
        coords = Coordinates(latitude=90, longitude=180)
        assert coords.latitude == 90
        assert coords.longitude == 180
    
    def test_invalid_latitude(self):
        """Latitud inválida debe fallar."""
        with pytest.raises(ValueError):
            Coordinates(latitude=91, longitude=0)
        with pytest.raises(ValueError):
            Coordinates(latitude=-91, longitude=0)
    
    def test_invalid_longitude(self):
        """Longitud inválida debe fallar."""
        with pytest.raises(ValueError):
            Coordinates(latitude=0, longitude=181)
        with pytest.raises(ValueError):
            Coordinates(latitude=0, longitude=-181)


class TestPaginationMeta:
    """Tests para PaginationMeta schema."""
    
    def test_create_first_page(self):
        """Crear metadata para primera página."""
        meta = PaginationMeta.create(total=100, page=1, page_size=20)
        
        assert meta.total == 100
        assert meta.page == 1
        assert meta.page_size == 20
        assert meta.total_pages == 5
        assert meta.has_next is True
        assert meta.has_prev is False
    
    def test_create_last_page(self):
        """Crear metadata para última página."""
        meta = PaginationMeta.create(total=100, page=5, page_size=20)
        
        assert meta.has_next is False
        assert meta.has_prev is True
    
    def test_create_single_page(self):
        """Crear metadata para única página."""
        meta = PaginationMeta.create(total=10, page=1, page_size=20)
        
        assert meta.total_pages == 1
        assert meta.has_next is False
        assert meta.has_prev is False
    
    def test_create_empty_result(self):
        """Crear metadata para resultado vacío."""
        meta = PaginationMeta.create(total=0, page=1, page_size=20)
        
        assert meta.total == 0
        assert meta.total_pages == 0
        assert meta.has_next is False
        assert meta.has_prev is False


class TestFireEventListItem:
    """Tests para FireEventListItem schema."""
    
    def test_valid_item(self):
        """Item válido."""
        item = FireEventListItem(
            id=UUID("550e8400-e29b-41d4-a716-446655440000"),
            start_date=datetime(2024, 8, 15, 14, 30),
            end_date=datetime(2024, 8, 17, 22, 0),
            centroid=Coordinates(latitude=-27.46, longitude=-58.83),
            total_detections=15,
        )
        
        assert item.total_detections == 15
        assert item.centroid.latitude == -27.46
    
    def test_status_active(self):
        """Status activo para incendio reciente."""
        item = FireEventListItem(
            id=UUID("550e8400-e29b-41d4-a716-446655440000"),
            start_date=datetime.now() - timedelta(hours=12),
            end_date=datetime.now() + timedelta(hours=12),
            centroid=Coordinates(latitude=-27.46, longitude=-58.83),
            total_detections=5,
        )
        
        assert item.status == FireStatus.ACTIVE
    
    def test_status_extinguished(self):
        """Status extinguido para incendio antiguo."""
        item = FireEventListItem(
            id=UUID("550e8400-e29b-41d4-a716-446655440000"),
            start_date=datetime.now() - timedelta(days=30),
            end_date=datetime.now() - timedelta(days=28),
            centroid=Coordinates(latitude=-27.46, longitude=-58.83),
            total_detections=5,
        )
        
        assert item.status == FireStatus.EXTINGUISHED


# =============================================================================
# ENDPOINT TESTS
# =============================================================================

class TestListFiresEndpoint:
    """Tests para GET /fires endpoint."""
    
    def test_list_fires_default(self, client):
        """Listar incendios sin filtros."""
        response = client.get("/api/v1/fires")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "fires" in data
        assert "pagination" in data
        assert len(data["fires"]) > 0
        assert data["pagination"]["page"] == 1
    
    def test_list_fires_pagination(self, client):
        """Paginación funciona correctamente."""
        response = client.get("/api/v1/fires?page=1&page_size=2")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["fires"]) <= 2
        assert data["pagination"]["page_size"] == 2
    
    def test_list_fires_filter_province(self, client):
        """Filtrar por provincia."""
        response = client.get("/api/v1/fires?province=Corrientes")
        
        assert response.status_code == 200
        data = response.json()
        
        for fire in data["fires"]:
            assert fire["province"] == "Corrientes"
    
    def test_list_fires_filter_protected_area(self, client):
        """Filtrar por área protegida."""
        response = client.get("/api/v1/fires?in_protected_area=true")
        
        assert response.status_code == 200
        data = response.json()
        
        for fire in data["fires"]:
            assert fire["in_protected_area"] is True
    
    def test_list_fires_filter_confidence(self, client):
        """Filtrar por confianza mínima."""
        response = client.get("/api/v1/fires?min_confidence=80")
        
        assert response.status_code == 200
        data = response.json()
        
        for fire in data["fires"]:
            assert fire["avg_confidence"] is None or fire["avg_confidence"] >= 80
    
    def test_list_fires_filter_date_range(self, client):
        """Filtrar por rango de fechas."""
        response = client.get("/api/v1/fires?date_from=2024-08-01&date_to=2024-08-31")
        
        assert response.status_code == 200
        data = response.json()
        
        for fire in data["fires"]:
            start = datetime.fromisoformat(fire["start_date"].replace("Z", "+00:00"))
            assert start.month == 8 and start.year == 2024
    
    def test_list_fires_sort_asc(self, client):
        """Ordenar ascendente."""
        response = client.get("/api/v1/fires?sort_by=start_date&sort_desc=false")
        
        assert response.status_code == 200
        data = response.json()
        
        if len(data["fires"]) >= 2:
            first = data["fires"][0]["start_date"]
            second = data["fires"][1]["start_date"]
            assert first <= second
    
    def test_list_fires_sort_desc(self, client):
        """Ordenar descendente."""
        response = client.get("/api/v1/fires?sort_by=start_date&sort_desc=true")
        
        assert response.status_code == 200
        data = response.json()
        
        if len(data["fires"]) >= 2:
            first = data["fires"][0]["start_date"]
            second = data["fires"][1]["start_date"]
            assert first >= second
    
    def test_list_fires_search(self, client):
        """Búsqueda de texto."""
        response = client.get("/api/v1/fires?search=Iberá")
        
        assert response.status_code == 200
        data = response.json()
        
        # Debe encontrar incendios con "Iberá" en protected_area_name
        assert len(data["fires"]) > 0
    
    def test_list_fires_combined_filters(self, client):
        """Múltiples filtros combinados."""
        response = client.get(
            "/api/v1/fires"
            "?province=Corrientes"
            "&in_protected_area=true"
            "&min_confidence=80"
            "&sort_by=total_detections"
            "&sort_desc=true"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verificar filtros aplicados
        assert "Corrientes" in (data["filters_applied"].get("province") or [])
    
    def test_list_fires_invalid_page_size(self, client):
        """Page size inválido debe rechazarse."""
        response = client.get("/api/v1/fires?page_size=500")
        
        assert response.status_code == 422  # Validation error


class TestFireDetailEndpoint:
    """Tests para GET /fires/{id} endpoint."""
    
    def test_get_fire_detail(self, client):
        """Obtener detalle de incendio existente."""
        fire_id = str(MOCK_FIRES[0].id)
        response = client.get(f"/api/v1/fires/{fire_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "fire" in data
        assert data["fire"]["id"] == fire_id
        assert "detections" in data
    
    def test_get_fire_not_found(self, client):
        """Incendio no existente retorna 404."""
        response = client.get("/api/v1/fires/00000000-0000-0000-0000-000000000000")
        
        assert response.status_code == 404
    
    def test_get_fire_invalid_uuid(self, client):
        """UUID inválido retorna 422."""
        response = client.get("/api/v1/fires/not-a-uuid")
        
        assert response.status_code == 422


class TestExportEndpoint:
    """Tests para GET /fires/export endpoint."""
    
    def test_export_csv(self, client):
        """Exportar a CSV."""
        response = client.get("/api/v1/fires/export?format=csv")
        
        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]
        assert "attachment" in response.headers["content-disposition"]
        assert ".csv" in response.headers["content-disposition"]
        
        # Verificar contenido CSV
        content = response.text
        assert "id,start_date" in content
    
    def test_export_json(self, client):
        """Exportar a JSON."""
        response = client.get("/api/v1/fires/export?format=json")
        
        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]
        assert ".json" in response.headers["content-disposition"]
        
        # Verificar contenido JSON
        data = response.json()
        assert "fires" in data
        assert "total_records" in data
    
    def test_export_with_filters(self, client):
        """Exportar con filtros aplicados."""
        response = client.get(
            "/api/v1/fires/export"
            "?format=csv"
            "&province=Corrientes"
            "&is_significant=true"
        )
        
        assert response.status_code == 200


class TestStatsEndpoint:
    """Tests para GET /fires/stats endpoint."""
    
    def test_get_stats_default(self, client):
        """Obtener estadísticas con valores por defecto."""
        response = client.get("/api/v1/fires/stats")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "stats" in data
        assert "period" in data
        assert data["stats"]["total_fires"] >= 0
    
    def test_get_stats_with_period(self, client):
        """Obtener estadísticas con período específico."""
        response = client.get(
            "/api/v1/fires/stats"
            "?date_from=2024-01-01"
            "&date_to=2024-12-31"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["period"]["from"] == "2024-01-01"
        assert data["period"]["to"] == "2024-12-31"
    
    def test_get_stats_by_province(self, client):
        """Obtener estadísticas filtradas por provincia."""
        response = client.get("/api/v1/fires/stats?province=Corrientes")
        
        assert response.status_code == 200
        data = response.json()
        
        # Si hay datos, todos deben ser de Corrientes
        if data["stats"]["total_fires"] > 0:
            provinces = [p["name"] for p in data["stats"]["by_province"]]
            assert "Corrientes" in provinces


class TestProvincesEndpoint:
    """Tests para GET /fires/provinces endpoint."""
    
    def test_list_provinces(self, client):
        """Listar provincias."""
        response = client.get("/api/v1/fires/provinces")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "provinces" in data
        assert "total" in data
        assert len(data["provinces"]) > 0
        
        # Verificar estructura
        province = data["provinces"][0]
        assert "name" in province
        assert "fire_count" in province


class TestHealthEndpoint:
    """Tests para health check."""
    
    def test_health(self, client):
        """Health check responde correctamente."""
        response = client.get("/api/v1/fires/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert data["service"] == "fires"


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])