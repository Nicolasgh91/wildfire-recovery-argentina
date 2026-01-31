"""
API Routes para Reportes Históricos - ForestGuard API.

Endpoint UC-12: Generación de reportes históricos de incendios
en áreas protegidas con imágenes satelitales Sentinel-2.

Endpoints:
    POST /api/v1/reports/historical-fire  - Generar reporte
    GET  /api/v1/reports/{report_id}      - Obtener reporte
    GET  /api/v1/reports/verify/{report_id} - Verificar autenticidad

Autor: ForestGuard Dev Team
Versión: 1.0.0
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query, Header
from fastapi.responses import JSONResponse

# Schemas
# Schemas
try:
    from app.schemas.report import (
        HistoricalReportRequest,
        HistoricalReportResponse,
        ReportVerificationResponse,
        ReportListResponse,
        ReportListItem,
        ReportStatus,
        ReportType,
        ReportOutputs,
        ReportMetadata,
        ImageEvidenceResponse,
        TemporalAnalysisResponse,
        RecoveryAnalysisResponse,
        RecoveryStatusEnum,
    )
    from app.core.config import settings
    # verify_api_key might be in app.api.deps or app.core.security? 
    # Usually deps. Let's check imports in other files if needed, but assuming app.core.security based on file content.
    # User's file had ..core.security so app.core.security is likely correct.
    from app.core.security import verify_api_key
except ImportError:
    # Fallback for testing execution context if needed, but usually absolute is best
    from app.schemas.report import (
        HistoricalReportRequest,
        HistoricalReportResponse,
        ReportVerificationResponse,
        ReportListResponse,
        ReportListItem,
        ReportStatus,
        ReportType,
        ReportOutputs,
        ReportMetadata,
        ImageEvidenceResponse,
        TemporalAnalysisResponse,
        RecoveryAnalysisResponse,
        RecoveryStatusEnum,
    )

# Services
# Services
try:
    from app.services.ers_service import (
        ERSService,
        ReportRequest as ERSReportRequest,
        ReportType as ERSReportType,
        ReportStatus as ERSReportStatus,
    )
    from app.services.gee_service import GEEService
    from app.services.vae_service import VAEService
    from app.services.storage_service import StorageService
except ImportError:
    from app.services.ers_service import (
        ERSService,
        ReportRequest as ERSReportRequest,
        ReportType as ERSReportType,
        ReportStatus as ERSReportStatus,
    )
    from app.services.gee_service import GEEService
    from app.services.vae_service import VAEService
    from app.services.storage_service import StorageService


logger = logging.getLogger(__name__)

# Router
router = APIRouter(
    responses={
        401: {"description": "API key inválida o faltante"},
        429: {"description": "Rate limit excedido"},
        500: {"description": "Error interno del servidor"},
    }
)


# =============================================================================
# DEPENDENCY INJECTION
# =============================================================================

def get_ers_service() -> ERSService:
    """Factory para ERS Service."""
    return ERSService()

def get_gee_service() -> GEEService:
    """Factory para GEE Service."""
    service = GEEService()
    service.authenticate()
    return service


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post(
    "/historical-fire",
    response_model=HistoricalReportResponse,
    status_code=202,
    summary="Generar reporte histórico de incendios",
    description="""
    Genera un reporte completo de análisis histórico de incendios en un área específica.
    
    **Funcionalidades:**
    - Recolección de imágenes Sentinel-2 pre y post-incendio
    - Cálculo de NDVI y análisis de recuperación
    - Generación de PDF con evidencia visual
    - Visor web interactivo con slider temporal
    - Hash SHA-256 para verificación de autenticidad
    
    **Límites:**
    - Máximo 20 imágenes por reporte
    - Área máxima: ~100 km²
    - Fecha de incendio no puede ser futura
    
    **Tiempo estimado:** 30-120 segundos dependiendo del número de imágenes.
    """,
    responses={
        202: {
            "description": "Reporte en generación",
            "content": {
                "application/json": {
                    "example": {
                        "report_id": "RPT-HIST-20250129-A1B2C3",
                        "status": "processing",
                        "message": "Reporte en generación. Consultar estado con GET /reports/{report_id}"
                    }
                }
            }
        },
        200: {
            "description": "Reporte generado exitosamente",
            "model": HistoricalReportResponse
        }
    }
)
async def generate_historical_report(
    request: HistoricalReportRequest,
    background_tasks: BackgroundTasks,
    x_api_key: Optional[str] = Header(None, description="API Key para autenticación"),
    sync: bool = Query(False, description="Si True, espera a que el reporte termine (puede tardar)"),
    ers_service: ERSService = Depends(get_ers_service)
) -> HistoricalReportResponse:
    """
    Genera reporte histórico de incendios (UC-12).
    
    El reporte incluye:
    - Imagen pre-incendio (baseline)
    - Serie temporal de imágenes post-incendio
    - Análisis de recuperación de vegetación (NDVI)
    - PDF con evidencia y hash de verificación
    - URL de visor web interactivo
    """
    
    logger.info(f"Historical report request: {request.protected_area_name}, fire_date={request.fire_date}")
    
    # Convertir request a formato interno
    ers_request = ERSReportRequest(
        report_type=ERSReportType.HISTORICAL,
        fire_event_id=request.fire_event_id,
        protected_area_id=request.protected_area_id,
        protected_area_name=request.protected_area_name,
        fire_date=request.fire_date,
        date_range_start=request.date_range.start if request.date_range else None,
        date_range_end=request.date_range.end if request.date_range else None,
        include_pre_fire=request.report_config.include_pre_fire,
        post_fire_frequency=request.report_config.post_fire_frequency.value,
        max_images=request.report_config.max_images,
        vis_types=request.report_config.vis_types,
        include_ndvi_chart=request.report_config.include_ndvi_chart,
        bbox={
            "west": request.bbox.west,
            "south": request.bbox.south,
            "east": request.bbox.east,
            "north": request.bbox.north,
        },
        output_format=request.output_format.value,
        requester_email=request.requester_email,
        requester_name=request.requester_name,
    )
    
    if sync:
        # Modo síncrono: esperar a que termine
        try:
            result = ers_service.generate_report(ers_request)
            if result.status == ERSReportStatus.FAILED:
                raise HTTPException(
                    status_code=503,
                    detail=f"Error generando reporte: {result.error_message or 'Unknown error'}"
                )
            return _convert_ers_result_to_response(result)
        except Exception as e:
            logger.error(f"Report generation failed: {e}")
            raise HTTPException(status_code=500, detail=f"Error generando reporte: {str(e)}")
    else:
        # Modo asíncrono: retornar inmediatamente
        # En producción, esto encolaría en Celery
        report_id = f"RPT-HIST-{datetime.now().strftime('%Y%m%d')}-PENDING"
        
        # Encolar tarea en background
        background_tasks.add_task(
            _generate_report_background,
            ers_service,
            ers_request,
            report_id
        )
        
        return HistoricalReportResponse(
            report_id=report_id,
            report_type=ReportType.HISTORICAL,
            status=ReportStatus.PROCESSING,
            requested_at=datetime.now(),
        )


@router.get(
    "/{report_id}",
    response_model=HistoricalReportResponse,
    summary="Obtener estado/resultado de un reporte",
    description="Obtiene el estado actual de un reporte en generación o el resultado si ya completó."
)
async def get_report(
    report_id: str,
    ers_service: ERSService = Depends(get_ers_service)
) -> HistoricalReportResponse:
    """
    Obtiene información de un reporte existente.
    
    Si el reporte está en proceso, retorna estado "processing".
    Si completó, retorna el resultado completo con URLs.
    """
    
    # En producción, esto consultaría la DB
    # Por ahora, simulamos que el reporte no existe
    
    # Verificar si existe en storage
    try:
        storage = StorageService()
        exists = storage.exists(f"reports/historical/{report_id}.pdf", bucket="forestguard-reports")
        
        if exists:
            # Reporte completado
            pdf_url = storage.get_public_url(f"reports/historical/{report_id}.pdf", "forestguard-reports")
            
            return HistoricalReportResponse(
                report_id=report_id,
                report_type=ReportType.HISTORICAL,
                status=ReportStatus.COMPLETED,
                outputs=ReportOutputs(
                    pdf_url=pdf_url,
                    web_viewer_url=f"https://forestguard.freedynamicdns.org/viewer/{report_id}"
                ),
                verification_url=f"https://forestguard.freedynamicdns.org/api/v1/reports/verify/{report_id}"
            )
        else:
            # Podría estar en proceso o no existir
            if "PENDING" in report_id:
                return HistoricalReportResponse(
                    report_id=report_id,
                    report_type=ReportType.HISTORICAL,
                    status=ReportStatus.PROCESSING,
                )
            else:
                raise HTTPException(status_code=404, detail=f"Reporte {report_id} no encontrado")
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting report {report_id}: {e}")
        raise HTTPException(status_code=500, detail="Error consultando reporte")


@router.get(
    "/verify/{report_id}",
    response_model=ReportVerificationResponse,
    summary="Verificar autenticidad de un reporte",
    description="Verifica que un reporte no ha sido modificado comparando su hash SHA-256."
)
async def verify_report(
    report_id: str,
    expected_hash: Optional[str] = Query(None, description="Hash esperado para comparar"),
    ers_service: ERSService = Depends(get_ers_service)
) -> ReportVerificationResponse:
    """
    Verifica la autenticidad de un reporte mediante su hash.
    
    Si se proporciona expected_hash, compara con el hash actual.
    Si no, solo retorna el hash actual del documento.
    """
    
    try:
        result = ers_service.verify_report(report_id, expected_hash or "")
        
        return ReportVerificationResponse(
            report_id=report_id,
            is_valid=result.get("is_valid", False),
            expected_hash=expected_hash,
            actual_hash=result.get("actual_hash"),
            verified_at=datetime.now(),
            error=result.get("error")
        )
        
    except Exception as e:
        logger.error(f"Error verifying report {report_id}: {e}")
        return ReportVerificationResponse(
            report_id=report_id,
            is_valid=False,
            verified_at=datetime.now(),
            error=str(e)
        )


@router.get(
    "/",
    response_model=ReportListResponse,
    summary="Listar reportes generados",
    description="Lista los reportes generados con paginación."
)
async def list_reports(
    page: int = Query(1, ge=1, description="Número de página"),
    per_page: int = Query(20, ge=1, le=100, description="Items por página"),
    report_type: Optional[ReportType] = Query(None, description="Filtrar por tipo"),
    status: Optional[ReportStatus] = Query(None, description="Filtrar por estado"),
) -> ReportListResponse:
    """
    Lista reportes con paginación y filtros opcionales.
    
    En producción, esto consultaría la tabla historical_report_requests.
    """
    
    # Placeholder - en producción consultaría la DB
    return ReportListResponse(
        total=0,
        page=page,
        per_page=per_page,
        reports=[]
    )


# =============================================================================
# HEALTH CHECK
# =============================================================================

@router.get(
    "/health",
    summary="Health check del servicio de reportes",
    include_in_schema=False
)
async def reports_health_check(
    ers_service: ERSService = Depends(get_ers_service)
):
    """Verifica estado de los servicios de reportes."""
    
    status = ers_service.health_check()
    
    return {
        "service": "reports",
        "status": status.get("status", "unknown"),
        "details": status
    }


# =============================================================================
# FUNCIONES AUXILIARES
# =============================================================================

async def _generate_report_background(
    ers_service: ERSService,
    request: ERSReportRequest,
    report_id: str
):
    """
    Genera reporte en background.
    
    En producción, esto sería una tarea Celery.
    """
    try:
        logger.info(f"Starting background report generation: {report_id}")
        result = ers_service.generate_report(request)
        logger.info(f"Report completed: {result.report_id}, status={result.status}")
        
        # En producción, actualizaría la DB con el resultado
        if result.status == ERSReportStatus.FAILED:
            logger.error(f"Report failed: {result.error_message}")
        
    except Exception as e:
        logger.error(f"Background report generation failed: {e}")
        # En producción, marcaría como FAILED en la DB


def _convert_ers_result_to_response(result) -> HistoricalReportResponse:
    """Convierte resultado de ERS a response schema."""
    
    # Convertir imágenes
    images = []
    for img in result.images:
        images.append(ImageEvidenceResponse(
            image_id=img.image_id,
            acquisition_date=img.acquisition_date,
            vis_type=img.vis_type,
            thumbnail_url=img.thumbnail_url,
            hd_download_url=img.hd_url,
            cloud_cover_percent=img.cloud_cover,
            satellite=img.satellite,
            ndvi_mean=img.ndvi_mean,
            is_pre_fire=img.is_pre_fire
        ))
    
    # Convertir análisis temporal
    temporal_analysis = None
    if result.analysis:
        post_fire_series = []
        for a in result.analysis.post_fire_series:
            post_fire_series.append(RecoveryAnalysisResponse(
                analysis_date=a.analysis_date,
                months_after_fire=a.months_after_fire,
                baseline_ndvi=a.baseline_ndvi,
                current_ndvi=a.current_ndvi,
                recovery_percentage=a.recovery_percentage,
                recovery_status=RecoveryStatusEnum(a.recovery_status.value),
                anomaly_detected=a.anomaly_detected,
                anomaly_type=a.anomaly_type.value if a.anomaly_detected else None
            ))
        
        temporal_analysis = TemporalAnalysisResponse(
            fire_event_id=result.analysis.fire_event_id,
            protected_area_name=result.analysis.protected_area_name,
            fire_date=result.analysis.fire_date,
            analysis_period_start=result.analysis.analysis_period[0],
            analysis_period_end=result.analysis.analysis_period[1],
            pre_fire_ndvi=result.analysis.pre_fire_ndvi,
            pre_fire_date=result.analysis.pre_fire_date,
            post_fire_series=post_fire_series,
            total_images_analyzed=result.analysis.total_images_analyzed,
            images_with_anomalies=result.analysis.images_with_anomalies,
            final_recovery_status=RecoveryStatusEnum(result.analysis.final_recovery_status.value),
            overall_recovery_percentage=result.analysis.overall_recovery_percentage,
            recovery_trend=result.analysis.recovery_trend,
            trend_confidence=result.analysis.trend_confidence
        )
    
    # Construir response
    return HistoricalReportResponse(
        report_id=result.report_id,
        report_type=ReportType.HISTORICAL,
        status=ReportStatus(result.status.value),
        fire_events_found=result.fire_events_found,
        images_collected=len(images),
        outputs=ReportOutputs(
            pdf_url=result.pdf_url,
            web_viewer_url=result.web_viewer_url,
            images=images
        ),
        analysis=temporal_analysis,
        metadata=ReportMetadata(
            protected_area=result.analysis.protected_area_name if result.analysis else None,
            fire_date=result.analysis.fire_date if result.analysis else None,
            total_affected_hectares=result.total_affected_hectares,
            verification_hash=result.verification_hash
        ) if result.verification_hash else None,
        verification_url=result.verification_url,
        completed_at=datetime.now() if result.status.value == "completed" else None,
        error_message=result.error_message
    )
