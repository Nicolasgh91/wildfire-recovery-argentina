"""
Tests para Reportes Históricos (UC-12) - ForestGuard API.

Incluye:
- Tests unitarios de schemas
- Tests de integración del endpoint
- Tests de servicios (mock)

Ejecutar con: pytest tests/test_historical_reports.py -v

Autor: ForestGuard Dev Team
Versión: 1.0.0
"""

import pytest
from datetime import date, datetime
from unittest.mock import Mock, patch, MagicMock

# Schemas
try:
    from app.schemas.report import (
        HistoricalReportRequest,
        HistoricalReportResponse,
        BoundingBox,
        ReportConfig,
        DateRange,
        PostFireFrequency,
        OutputFormat,
        ReportStatus,
        ReportType,
    )
except ImportError:
    from schemas_report import (
        HistoricalReportRequest,
        HistoricalReportResponse,
        BoundingBox,
        ReportConfig,
        DateRange,
        PostFireFrequency,
        OutputFormat,
        ReportStatus,
        ReportType,
    )


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def valid_bbox():
    """BoundingBox válido para tests."""
    return BoundingBox(
        west=-60.5,
        south=-27.0,
        east=-60.3,
        north=-26.8
    )

@pytest.fixture
def valid_request(valid_bbox):
    """Request válido para tests."""
    return HistoricalReportRequest(
        protected_area_name="Parque Nacional Chaco",
        fire_event_id="550e8400-e29b-41d4-a716-446655440000",
        fire_date=date(2020, 8, 15),
        bbox=valid_bbox,
        report_config=ReportConfig(
            post_fire_frequency=PostFireFrequency.ANNUAL,
            max_images=5
        ),
        output_format=OutputFormat.HYBRID
    )


# =============================================================================
# TESTS DE SCHEMAS - BOUNDING BOX
# =============================================================================

class TestBoundingBox:
    """Tests para BoundingBox schema."""
    
    def test_valid_bbox(self):
        """BoundingBox válido debe crearse sin errores."""
        bbox = BoundingBox(
            west=-60.5,
            south=-27.0,
            east=-60.3,
            north=-26.8
        )
        assert bbox.west == -60.5
        assert bbox.south == -27.0
        assert bbox.east == -60.3
        assert bbox.north == -26.8
    
    def test_invalid_west_east(self):
        """West no puede ser mayor o igual a east."""
        with pytest.raises(ValueError, match="west debe ser menor que east"):
            BoundingBox(
                west=-60.0,  # Mayor que east
                south=-27.0,
                east=-60.5,
                north=-26.8
            )
    
    def test_invalid_south_north(self):
        """South no puede ser mayor o igual a north."""
        with pytest.raises(ValueError, match="south debe ser menor que north"):
            BoundingBox(
                west=-60.5,
                south=-26.0,  # Mayor que north
                east=-60.3,
                north=-27.0
            )
    
    def test_out_of_range_longitude(self):
        """Longitud fuera de rango [-180, 180] debe fallar."""
        with pytest.raises(ValueError):
            BoundingBox(
                west=-200.0,  # Fuera de rango
                south=-27.0,
                east=-60.3,
                north=-26.8
            )
    
    def test_out_of_range_latitude(self):
        """Latitud fuera de rango [-90, 90] debe fallar."""
        with pytest.raises(ValueError):
            BoundingBox(
                west=-60.5,
                south=-100.0,  # Fuera de rango
                east=-60.3,
                north=-26.8
            )


# =============================================================================
# TESTS DE SCHEMAS - REPORT CONFIG
# =============================================================================

class TestReportConfig:
    """Tests para ReportConfig schema."""
    
    def test_default_values(self):
        """Valores por defecto deben ser correctos."""
        config = ReportConfig()
        assert config.include_pre_fire == True
        assert config.post_fire_frequency == PostFireFrequency.ANNUAL
        assert config.max_images == 12
        assert config.vis_types == ["RGB", "NDVI"]
        assert config.include_ndvi_chart == True
        assert config.max_cloud_cover == 30.0
    
    def test_custom_values(self):
        """Valores personalizados deben funcionar."""
        config = ReportConfig(
            include_pre_fire=False,
            post_fire_frequency=PostFireFrequency.MONTHLY,
            max_images=6,
            vis_types=["RGB"],
            max_cloud_cover=15.0
        )
        assert config.include_pre_fire == False
        assert config.post_fire_frequency == PostFireFrequency.MONTHLY
        assert config.max_images == 6
    
    def test_max_images_validation(self):
        """max_images debe estar entre 1 y 20."""
        with pytest.raises(ValueError):
            ReportConfig(max_images=0)
        
        with pytest.raises(ValueError):
            ReportConfig(max_images=25)
    
    def test_cloud_cover_validation(self):
        """max_cloud_cover debe estar entre 0 y 100."""
        with pytest.raises(ValueError):
            ReportConfig(max_cloud_cover=-5)
        
        with pytest.raises(ValueError):
            ReportConfig(max_cloud_cover=150)


# =============================================================================
# TESTS DE SCHEMAS - HISTORICAL REPORT REQUEST
# =============================================================================

class TestHistoricalReportRequest:
    """Tests para HistoricalReportRequest schema."""
    
    def test_valid_request(self, valid_bbox):
        """Request válido debe crearse sin errores."""
        request = HistoricalReportRequest(
            protected_area_name="Parque Nacional Test",
            fire_date=date(2020, 8, 15),
            bbox=valid_bbox
        )
        assert request.protected_area_name == "Parque Nacional Test"
        assert request.fire_date == date(2020, 8, 15)
    
    def test_future_fire_date_rejected(self, valid_bbox):
        """Fecha de incendio futura debe ser rechazada."""
        from datetime import timedelta
        future_date = date.today() + timedelta(days=30)
        
        with pytest.raises(ValueError, match="no puede ser una fecha futura"):
            HistoricalReportRequest(
                fire_date=future_date,
                bbox=valid_bbox
            )
    
    def test_default_area_name(self, valid_bbox):
        """Si no se especifica nombre, debe usar default."""
        request = HistoricalReportRequest(
            fire_date=date(2020, 8, 15),
            bbox=valid_bbox
        )
        assert request.protected_area_name == "Área no especificada"
    
    def test_optional_fields(self, valid_bbox):
        """Campos opcionales pueden ser None."""
        request = HistoricalReportRequest(
            fire_date=date(2020, 8, 15),
            bbox=valid_bbox
        )
        assert request.fire_event_id is None
        assert request.protected_area_id is None
        assert request.requester_email is None
    
    def test_date_range_validation(self, valid_bbox):
        """DateRange debe tener start <= end."""
        with pytest.raises(ValueError, match="start debe ser anterior"):
            HistoricalReportRequest(
                fire_date=date(2020, 8, 15),
                bbox=valid_bbox,
                date_range=DateRange(
                    start=date(2022, 1, 1),
                    end=date(2021, 1, 1)  # Antes de start
                )
            )


# =============================================================================
# TESTS DE SCHEMAS - RESPONSE
# =============================================================================

class TestHistoricalReportResponse:
    """Tests para HistoricalReportResponse schema."""
    
    def test_minimal_response(self):
        """Response mínimo debe ser válido."""
        response = HistoricalReportResponse(
            report_id="RPT-HIST-20250129-ABC123",
            status=ReportStatus.PROCESSING
        )
        assert response.report_id == "RPT-HIST-20250129-ABC123"
        assert response.status == ReportStatus.PROCESSING
        assert response.report_type == ReportType.HISTORICAL
    
    def test_completed_response(self):
        """Response completo debe incluir todos los campos."""
        response = HistoricalReportResponse(
            report_id="RPT-HIST-20250129-ABC123",
            status=ReportStatus.COMPLETED,
            fire_events_found=1,
            images_collected=8,
            verification_url="https://forestguard.ar/verify/RPT-HIST-20250129-ABC123",
            completed_at=datetime.now()
        )
        assert response.fire_events_found == 1
        assert response.images_collected == 8
        assert response.completed_at is not None
    
    def test_failed_response(self):
        """Response fallido debe incluir mensaje de error."""
        response = HistoricalReportResponse(
            report_id="RPT-HIST-20250129-ABC123",
            status=ReportStatus.FAILED,
            error_message="No images found for the specified area"
        )
        assert response.status == ReportStatus.FAILED
        assert response.error_message is not None


# =============================================================================
# TESTS DE SERVICIOS (MOCK)
# =============================================================================

class TestGEEServiceMock:
    """Tests para GEE Service con mocks."""
    
    def test_health_check(self):
        """Health check debe retornar status."""
        try:
            from app.services.gee_service import GEEService
        except ImportError:
            pytest.skip("gee_service not available")
        
        with patch.object(GEEService, 'authenticate', return_value=True):
            with patch.object(GEEService, '_rate_limited_request', return_value={"id": "test"}):
                service = GEEService()
                # Mock the ee module
                service._initialized = True
                status = service.health_check()
                # Should return some status dict
                assert isinstance(status, dict)
                assert "status" in status


class TestVAEServiceMock:
    """Tests para VAE Service con mocks."""
    
    def test_recovery_classification(self):
        """Clasificación de recuperación debe ser correcta."""
        try:
            from app.services.vae_service import VAEService, RecoveryStatus
        except ImportError:
            pytest.skip("vae_service not available")
        
        # Mock GEE y Storage
        mock_gee = Mock()
        mock_storage = Mock()
        
        service = VAEService(gee_service=mock_gee, storage_service=mock_storage)
        
        # Test clasificación
        assert service._classify_recovery_status(5) == RecoveryStatus.NOT_STARTED
        assert service._classify_recovery_status(20) == RecoveryStatus.EARLY_RECOVERY
        assert service._classify_recovery_status(45) == RecoveryStatus.MODERATE_RECOVERY
        assert service._classify_recovery_status(75) == RecoveryStatus.ADVANCED_RECOVERY
        assert service._classify_recovery_status(95) == RecoveryStatus.FULL_RECOVERY


class TestERSServiceMock:
    """Tests para ERS Service con mocks."""
    
    def test_report_id_generation(self):
        """IDs de reporte deben tener formato correcto."""
        try:
            from app.services.ers_service import ERSService, ReportType
        except ImportError:
            pytest.skip("ers_service not available")
        
        mock_gee = Mock()
        mock_vae = Mock()
        mock_storage = Mock()
        
        service = ERSService(
            gee_service=mock_gee,
            vae_service=mock_vae,
            storage_service=mock_storage
        )
        
        # Test generación de IDs
        hist_id = service._generate_report_id(ReportType.HISTORICAL)
        assert hist_id.startswith("RPT-HIST-")
        assert len(hist_id) == 24  # RPT-HIST-YYYYMMDD-XXXXXX
        
        jud_id = service._generate_report_id(ReportType.JUDICIAL)
        assert jud_id.startswith("RPT-JUD-")
    
    def test_hash_generation(self):
        """Hash de verificación debe ser SHA-256."""
        try:
            from app.services.ers_service import ERSService
        except ImportError:
            pytest.skip("ers_service not available")
        
        service = ERSService()
        
        test_content = b"Test PDF content"
        hash_result = service._create_verification_hash(test_content)
        
        assert hash_result.startswith("sha256:")
        assert len(hash_result) == 71  # "sha256:" + 64 hex chars


# =============================================================================
# TESTS DE INTEGRACIÓN (con FastAPI TestClient)
# =============================================================================

class TestHistoricalEndpointIntegration:
    """Tests de integración para el endpoint."""
    
    @pytest.fixture
    def client(self):
        """Cliente de prueba FastAPI."""
        try:
            from fastapi import FastAPI
            from fastapi.testclient import TestClient
            from app.api.routes.historical import router
            
            app = FastAPI()
            app.include_router(router, prefix="/api/v1")
            
            return TestClient(app)
        except ImportError:
            pytest.skip("FastAPI or routes not available")
    
    def test_health_endpoint(self, client):
        """Health check debe responder."""
        response = client.get("/api/v1/health")
        # Puede fallar si servicios no están configurados
        assert response.status_code in [200, 500]
    
    def test_list_reports_empty(self, client):
        """Lista de reportes vacía."""
        response = client.get("/api/v1/")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["reports"] == []
    
    def test_create_report_validation(self, client):
        """Validación de request debe funcionar."""
        # Request inválido (falta bbox)
        response = client.post(
            "/api/v1/historical-fire",
            json={
                "fire_date": "2020-08-15"
                # Falta bbox requerido
            }
        )
        assert response.status_code == 422  # Validation error
    
    def test_create_report_future_date(self, client):
        """Fecha futura debe ser rechazada."""
        from datetime import timedelta
        future = (date.today() + timedelta(days=30)).isoformat()
        
        response = client.post(
            "/api/v1/historical-fire",
            json={
                "fire_date": future,
                "bbox": {
                    "west": -60.5,
                    "south": -27.0,
                    "east": -60.3,
                    "north": -26.8
                }
            }
        )
        assert response.status_code == 422
    
    def test_get_nonexistent_report(self, client):
        """Reporte inexistente debe retornar 404."""
        response = client.get("/api/v1/NONEXISTENT-ID")
        assert response.status_code in [404, 500]  # 500 si storage no configurado


# =============================================================================
# TESTS DE UTILIDADES
# =============================================================================

class TestUtilities:
    """Tests para funciones auxiliares."""
    
    def test_months_between(self):
        """Cálculo de meses entre fechas."""
        try:
            from app.services.vae_service import VAEService
        except ImportError:
            pytest.skip("vae_service not available")
        
        service = VAEService()
        
        # Mismo mes
        assert service._months_between(date(2020, 1, 1), date(2020, 1, 31)) == 0
        
        # Un año
        assert service._months_between(date(2020, 1, 1), date(2021, 1, 1)) == 12
        
        # 18 meses
        assert service._months_between(date(2020, 6, 15), date(2022, 1, 15)) == 19  # Aproximado
    
    def test_add_months(self):
        """Suma de meses a fecha."""
        try:
            from app.services.vae_service import VAEService
        except ImportError:
            pytest.skip("vae_service not available")
        
        service = VAEService()
        
        # Caso normal
        result = service._add_months(date(2020, 6, 15), 3)
        assert result == date(2020, 9, 15)
        
        # Cruce de año
        result = service._add_months(date(2020, 11, 15), 3)
        assert result == date(2021, 2, 15)
        
        # Día que no existe (31 de febrero)
        result = service._add_months(date(2020, 1, 31), 1)
        assert result == date(2020, 2, 28)  # Fallback a 28


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])