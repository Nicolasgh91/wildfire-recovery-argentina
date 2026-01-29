"""
Evidence Reporting Service (ERS) para ForestGuard.

Servicio unificado de generación de reportes y evidencia:
- Peritajes judiciales (UC-02)
- Paquetes de evidencia para denuncias (UC-09)
- Reportes históricos en áreas protegidas (UC-12)

Genera PDFs verificables con hash SHA-256 y código QR.

Arquitectura:
    Endpoints → ERS Service → VAE Service (análisis)
                    ↓              ↓
              PDF Generation   GEE Service (imágenes)
                    ↓              ↓
              Storage Service (R2)

Autor: ForestGuard Dev Team
Versión: 1.0.0
Última actualización: 2025-01-29
"""

import hashlib
import logging
import tempfile
from io import BytesIO
from pathlib import Path
from datetime import date, datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple, BinaryIO
from dataclasses import dataclass, field
from enum import Enum
import json
import uuid

# PDF generation
try:
    from fpdf import FPDF
    import qrcode
    FPDF_AVAILABLE = True
except ImportError:
    FPDF_AVAILABLE = False
    logging.warning("fpdf2 or qrcode not installed. PDF generation disabled.")

# Importar servicios
try:
    from .gee_service import GEEService, GEEImageNotFoundError, ImageMetadata
    from .storage_service import StorageService, UploadResult
    from .vae_service import VAEService, TemporalAnalysis, RecoveryAnalysis
except ImportError:
    from gee_service import GEEService, GEEImageNotFoundError, ImageMetadata
    from storage_service import StorageService, UploadResult
    from vae_service import VAEService, TemporalAnalysis, RecoveryAnalysis

logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURACIÓN
# =============================================================================

# Colores corporativos
COLORS = {
    "PRIMARY": (46, 125, 50),      # Verde Forestal
    "SECONDARY": (27, 94, 32),     # Verde Oscuro
    "ACCENT": (200, 83, 0),        # Naranja
    "DANGER": (200, 0, 0),         # Rojo
    "TEXT": (50, 50, 50),          # Gris Oscuro
    "TEXT_LIGHT": (128, 128, 128), # Gris
    "BG_LIGHT": (245, 245, 245),   # Gris Muy Claro
    "WHITE": (255, 255, 255),
}

# Rutas de recursos
BASE_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = BASE_DIR / "assets"
LOGO_PATH = ASSETS_DIR / "logo-horizontal.png"

# Configuración de PDF
PDF_CONFIG = {
    "page_size": "A4",
    "margin_mm": 15,
    "font_family": "Arial",
    "image_quality": 85,
    "max_images_per_page": 4,
}


# =============================================================================
# ENUMS
# =============================================================================

class ReportType(Enum):
    """Tipos de reportes soportados."""
    HISTORICAL = "historical"           # UC-12
    JUDICIAL = "judicial"               # UC-02
    CITIZEN_EVIDENCE = "citizen_evidence"  # UC-09
    RECOVERY_MONITORING = "recovery"    # UC-06
    CERTIFICATE = "certificate"         # UC-07

class ReportStatus(Enum):
    """Estados del reporte."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class ReportRequest:
    """Solicitud de generación de reporte."""
    report_type: ReportType
    fire_event_id: Optional[str] = None
    protected_area_id: Optional[str] = None
    protected_area_name: Optional[str] = None
    
    # Temporal
    date_range_start: Optional[date] = None
    date_range_end: Optional[date] = None
    fire_date: Optional[date] = None
    
    # Configuración
    include_pre_fire: bool = True
    post_fire_frequency: str = "annual"  # daily, monthly, annual
    max_images: int = 12
    vis_types: List[str] = field(default_factory=lambda: ["RGB", "NDVI"])
    include_ndvi_chart: bool = True
    
    # Spatial
    bbox: Optional[Dict[str, float]] = None
    
    # Output
    output_format: str = "hybrid"  # pdf, web, hybrid
    
    # Requester
    requester_email: Optional[str] = None
    requester_name: Optional[str] = None

@dataclass
class ImageEvidence:
    """Evidencia de imagen satelital."""
    image_id: str
    acquisition_date: date
    vis_type: str
    thumbnail_url: str
    thumbnail_bytes: Optional[bytes] = None
    hd_url: Optional[str] = None
    cloud_cover: float = 0
    satellite: str = "Sentinel-2"
    ndvi_mean: Optional[float] = None
    is_pre_fire: bool = False

@dataclass
class ReportResult:
    """Resultado de generación de reporte."""
    report_id: str
    report_type: ReportType
    status: ReportStatus
    
    # URLs
    pdf_url: Optional[str] = None
    web_viewer_url: Optional[str] = None
    
    # Content
    images: List[ImageEvidence] = field(default_factory=list)
    analysis: Optional[TemporalAnalysis] = None
    
    # Verification
    verification_hash: str = ""
    verification_url: str = ""
    
    # Metadata
    generated_at: datetime = field(default_factory=datetime.now)
    fire_events_found: int = 0
    total_affected_hectares: float = 0
    
    # Errors
    error_message: Optional[str] = None


# =============================================================================
# PDF GENERATOR
# =============================================================================

class ForestGuardReportPDF(FPDF):
    """Clase PDF personalizada para reportes ForestGuard."""
    
    def __init__(self, report_type: ReportType, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.report_type = report_type
        self.report_id = ""
        
    def header(self):
        """Encabezado corporativo."""
        # Fondo verde
        self.set_fill_color(*COLORS["PRIMARY"])
        self.rect(0, 0, 210, 30, 'F')
        
        # Logo (si existe)
        offset_x = 10
        if LOGO_PATH.exists():
            try:
                self.image(str(LOGO_PATH), 10, 5, 20)
                offset_x = 35
            except:
                pass
        
        # Título
        self.set_font('Arial', 'B', 16)
        self.set_text_color(*COLORS["WHITE"])
        self.set_xy(offset_x, 8)
        self.cell(0, 8, 'ForestGuard', 0, 1, 'L')
        
        # Subtítulo según tipo
        subtitles = {
            ReportType.HISTORICAL: "Reporte Histórico de Incendios",
            ReportType.JUDICIAL: "Peritaje Judicial Forense",
            ReportType.CITIZEN_EVIDENCE: "Paquete de Evidencia",
            ReportType.RECOVERY_MONITORING: "Monitoreo de Recuperación",
            ReportType.CERTIFICATE: "Certificado Legal",
        }
        
        self.set_font('Arial', '', 10)
        self.set_xy(offset_x, 16)
        self.cell(0, 6, subtitles.get(self.report_type, "Reporte"), 0, 1, 'L')
        
        self.ln(15)
    
    def footer(self):
        """Pie de página con verificación."""
        self.set_y(-20)
        
        # Línea separadora
        self.set_draw_color(*COLORS["PRIMARY"])
        self.line(10, 280, 200, 280)
        
        # Texto
        self.set_font('Arial', 'I', 8)
        self.set_text_color(*COLORS["TEXT_LIGHT"])
        
        self.set_y(-15)
        self.cell(0, 5, f'ID: {self.report_id}', 0, 1, 'L')
        self.cell(0, 5, f'Página {self.page_no()}/{{nb}} | Generado: {datetime.now().strftime("%Y-%m-%d %H:%M")} | forestguard.freedynamicdns.org', 0, 0, 'C')


# =============================================================================
# SERVICIO PRINCIPAL
# =============================================================================

class ERSService:
    """
    Evidence Reporting Service - Motor de generación de reportes.
    
    Centraliza la generación de:
    - PDFs de reportes históricos (UC-12)
    - Peritajes judiciales (UC-02)
    - Paquetes de evidencia (UC-09)
    
    Ejemplo de uso:
        ers = ERSService()
        
        # Generar reporte histórico
        request = ReportRequest(
            report_type=ReportType.HISTORICAL,
            fire_event_id="uuid-123",
            protected_area_name="Parque Nacional Chaco",
            fire_date=date(2020, 8, 15),
            max_images=10
        )
        
        result = ers.generate_report(request)
    """
    
    def __init__(
        self,
        gee_service: Optional[GEEService] = None,
        vae_service: Optional[VAEService] = None,
        storage_service: Optional[StorageService] = None
    ):
        """Inicializa el servicio ERS."""
        self._gee = gee_service or GEEService()
        self._vae = vae_service or VAEService(gee_service=self._gee)
        self._storage = storage_service or StorageService()
    
    # =========================================================================
    # MÉTODO PRINCIPAL
    # =========================================================================
    
    def generate_report(self, request: ReportRequest) -> ReportResult:
        """
        Genera un reporte completo según la solicitud.
        
        Args:
            request: ReportRequest con configuración
            
        Returns:
            ReportResult con URLs y metadata
        """
        report_id = self._generate_report_id(request.report_type)
        
        logger.info(f"Generating {request.report_type.value} report: {report_id}")
        
        try:
            # Dispatch según tipo
            if request.report_type == ReportType.HISTORICAL:
                return self._generate_historical_report(request, report_id)
            elif request.report_type == ReportType.JUDICIAL:
                return self._generate_judicial_report(request, report_id)
            elif request.report_type == ReportType.CITIZEN_EVIDENCE:
                return self._generate_evidence_package(request, report_id)
            else:
                raise ValueError(f"Unsupported report type: {request.report_type}")
                
        except Exception as e:
            logger.error(f"Report generation failed: {e}")
            return ReportResult(
                report_id=report_id,
                report_type=request.report_type,
                status=ReportStatus.FAILED,
                error_message=str(e)
            )
    
    # =========================================================================
    # UC-12: REPORTES HISTÓRICOS
    # =========================================================================
    
    def _generate_historical_report(
        self,
        request: ReportRequest,
        report_id: str
    ) -> ReportResult:
        """Genera reporte histórico de incendios en área protegida."""
        
        self._gee.authenticate()
        
        if not request.bbox or not request.fire_date:
            raise ValueError("bbox and fire_date are required for historical reports")
        
        # 1. Obtener análisis temporal
        analysis = self._vae.analyze_temporal_series(
            fire_event_id=request.fire_event_id or "unknown",
            bbox=request.bbox,
            fire_date=request.fire_date,
            protected_area_name=request.protected_area_name or "Área Protegida",
            years_to_analyze=min(10, request.max_images)
        )
        
        # 2. Recolectar imágenes
        images = self._collect_images_for_report(
            bbox=request.bbox,
            fire_date=request.fire_date,
            max_images=request.max_images,
            vis_types=request.vis_types,
            include_pre_fire=request.include_pre_fire,
            frequency=request.post_fire_frequency
        )
        
        # 3. Generar PDF
        pdf_bytes = self._create_historical_pdf(
            report_id=report_id,
            request=request,
            analysis=analysis,
            images=images
        )
        
        # 4. Calcular hash de verificación
        verification_hash = self._create_verification_hash(pdf_bytes)
        
        # 5. Subir a storage
        pdf_result = self._storage.upload_report_pdf(
            report_id=report_id,
            pdf_bytes=pdf_bytes,
            report_type="historical"
        )
        
        # 6. Subir thumbnails a storage
        for img in images:
            if img.thumbnail_bytes:
                self._storage.upload_thumbnail(
                    fire_event_id=request.fire_event_id or report_id,
                    image_bytes=img.thumbnail_bytes,
                    vis_type=img.vis_type,
                    acquisition_date=img.acquisition_date
                )
        
        return ReportResult(
            report_id=report_id,
            report_type=ReportType.HISTORICAL,
            status=ReportStatus.COMPLETED,
            pdf_url=pdf_result.url if pdf_result.success else None,
            web_viewer_url=f"https://forestguard.freedynamicdns.org/viewer/{report_id}",
            images=images,
            analysis=analysis,
            verification_hash=verification_hash,
            verification_url=f"https://forestguard.freedynamicdns.org/verify/{report_id}",
            fire_events_found=1,
            total_affected_hectares=0  # TODO: calcular desde análisis
        )
    
    def _collect_images_for_report(
        self,
        bbox: Dict[str, float],
        fire_date: date,
        max_images: int,
        vis_types: List[str],
        include_pre_fire: bool,
        frequency: str
    ) -> List[ImageEvidence]:
        """Recolecta imágenes para el reporte."""
        
        images = []
        
        # Imagen pre-incendio
        if include_pre_fire:
            try:
                pre_fire_img = self._get_image_evidence(
                    bbox=bbox,
                    target_date=fire_date - timedelta(days=15),
                    vis_type="RGB",
                    is_pre_fire=True
                )
                if pre_fire_img:
                    images.append(pre_fire_img)
            except GEEImageNotFoundError:
                logger.warning("No pre-fire image available")
        
        # Imágenes post-incendio
        remaining = max_images - len(images)
        
        if frequency == "annual":
            # Una imagen por año
            for year_offset in range(1, remaining + 1):
                target = date(fire_date.year + year_offset, fire_date.month, 
                             min(fire_date.day, 28))
                if target > date.today():
                    break
                    
                try:
                    img = self._get_image_evidence(
                        bbox=bbox,
                        target_date=target,
                        vis_type="RGB"
                    )
                    if img:
                        images.append(img)
                        
                        # También NDVI si está en vis_types
                        if "NDVI" in vis_types:
                            ndvi_img = self._get_image_evidence(
                                bbox=bbox,
                                target_date=target,
                                vis_type="NDVI"
                            )
                            if ndvi_img:
                                images.append(ndvi_img)
                                
                except GEEImageNotFoundError:
                    continue
        
        elif frequency == "monthly":
            # Una imagen por mes (primeros 12 meses)
            for month_offset in range(1, min(remaining + 1, 13)):
                target = self._add_months(fire_date, month_offset)
                if target > date.today():
                    break
                    
                try:
                    img = self._get_image_evidence(
                        bbox=bbox,
                        target_date=target,
                        vis_type="RGB"
                    )
                    if img:
                        images.append(img)
                except GEEImageNotFoundError:
                    continue
        
        return images
    
    def _get_image_evidence(
        self,
        bbox: Dict[str, float],
        target_date: date,
        vis_type: str,
        is_pre_fire: bool = False
    ) -> Optional[ImageEvidence]:
        """Obtiene evidencia de imagen para una fecha."""
        
        # Ventana de búsqueda
        start = target_date - timedelta(days=30)
        end = target_date + timedelta(days=30)
        
        collection = self._gee.get_sentinel_collection(
            bbox=bbox,
            start_date=start,
            end_date=end,
            max_cloud_cover=30
        )
        
        image = self._gee.get_best_image(collection, target_date=target_date)
        metadata = self._gee.get_image_metadata(image)
        
        # Obtener thumbnail
        thumb_url = self._gee.get_thumbnail_url(image, bbox, vis_type=vis_type, dimensions=512)
        thumb_bytes = self._gee.download_thumbnail(image, bbox, vis_type=vis_type, dimensions=512)
        
        # Calcular NDVI si es RGB
        ndvi_mean = None
        if vis_type == "RGB":
            try:
                ndvi_result = self._gee.calculate_ndvi(image, bbox)
                ndvi_mean = ndvi_result.mean
            except:
                pass
        
        return ImageEvidence(
            image_id=metadata.image_id,
            acquisition_date=metadata.acquisition_date,
            vis_type=vis_type,
            thumbnail_url=thumb_url,
            thumbnail_bytes=thumb_bytes,
            cloud_cover=metadata.cloud_cover_percent,
            satellite=metadata.satellite,
            ndvi_mean=ndvi_mean,
            is_pre_fire=is_pre_fire
        )
    
    def _create_historical_pdf(
        self,
        report_id: str,
        request: ReportRequest,
        analysis: TemporalAnalysis,
        images: List[ImageEvidence]
    ) -> bytes:
        """Crea el PDF del reporte histórico."""
        
        if not FPDF_AVAILABLE:
            raise RuntimeError("fpdf2 not installed")
        
        pdf = ForestGuardReportPDF(report_type=ReportType.HISTORICAL)
        pdf.report_id = report_id
        pdf.alias_nb_pages()
        pdf.add_page()
        
        # === PÁGINA 1: RESUMEN EJECUTIVO ===
        
        # Título
        pdf.set_font('Arial', 'B', 18)
        pdf.set_text_color(*COLORS["SECONDARY"])
        pdf.cell(0, 10, 'REPORTE HISTÓRICO DE INCENDIOS', 0, 1, 'C')
        pdf.ln(5)
        
        # Número de reporte
        pdf.set_font('Courier', 'B', 12)
        pdf.set_text_color(*COLORS["ACCENT"])
        pdf.cell(0, 8, f'REF: {report_id}', 0, 1, 'C')
        pdf.ln(10)
        
        # Información del área
        pdf.set_fill_color(*COLORS["BG_LIGHT"])
        pdf.rect(10, pdf.get_y(), 190, 40, 'F')
        
        pdf.set_y(pdf.get_y() + 5)
        pdf.set_font('Arial', 'B', 11)
        pdf.set_text_color(*COLORS["TEXT"])
        
        info_items = [
            ("Área Protegida:", request.protected_area_name or "No especificada"),
            ("Fecha del Incendio:", analysis.fire_date.strftime("%d/%m/%Y")),
            ("Período Analizado:", f"{analysis.analysis_period[0].strftime('%d/%m/%Y')} - {analysis.analysis_period[1].strftime('%d/%m/%Y')}"),
            ("Imágenes Analizadas:", str(analysis.total_images_analyzed)),
        ]
        
        for label, value in info_items:
            pdf.set_x(15)
            pdf.set_font('Arial', 'B', 10)
            pdf.cell(45, 8, label, 0, 0)
            pdf.set_font('Arial', '', 10)
            pdf.cell(0, 8, value, 0, 1)
        
        pdf.ln(15)
        
        # Estado de recuperación
        pdf.set_font('Arial', 'B', 14)
        pdf.set_text_color(*COLORS["SECONDARY"])
        pdf.cell(0, 10, 'Estado de Recuperación', 0, 1, 'L')
        
        # Box de estado
        status_color = COLORS["PRIMARY"] if analysis.overall_recovery_percentage > 70 else COLORS["ACCENT"]
        if analysis.overall_recovery_percentage < 40:
            status_color = COLORS["DANGER"]
        
        pdf.set_fill_color(*status_color)
        pdf.set_text_color(*COLORS["WHITE"])
        pdf.set_font('Arial', 'B', 24)
        pdf.set_x(60)
        pdf.cell(90, 20, f'{analysis.overall_recovery_percentage:.0f}%', 1, 1, 'C', True)
        
        pdf.set_text_color(*COLORS["TEXT"])
        pdf.set_font('Arial', '', 10)
        pdf.cell(0, 8, f'Estado: {analysis.final_recovery_status.value.replace("_", " ").title()}', 0, 1, 'C')
        pdf.cell(0, 8, f'Tendencia: {analysis.recovery_trend.title()} (confianza: {analysis.trend_confidence:.0%})', 0, 1, 'C')
        
        if analysis.images_with_anomalies > 0:
            pdf.set_text_color(*COLORS["DANGER"])
            pdf.set_font('Arial', 'B', 10)
            pdf.cell(0, 8, f'⚠ Anomalías detectadas: {analysis.images_with_anomalies}', 0, 1, 'C')
        
        pdf.ln(10)
        
        # === PÁGINAS DE IMÁGENES ===
        
        # Separar pre-fire y post-fire
        pre_fire_images = [img for img in images if img.is_pre_fire]
        post_fire_images = [img for img in images if not img.is_pre_fire]
        
        # Imagen pre-incendio
        if pre_fire_images:
            pdf.add_page()
            pdf.set_font('Arial', 'B', 14)
            pdf.set_text_color(*COLORS["SECONDARY"])
            pdf.cell(0, 10, 'Imagen Pre-Incendio (Baseline)', 0, 1, 'L')
            pdf.ln(5)
            
            img = pre_fire_images[0]
            self._add_image_to_pdf(pdf, img, width=180)
        
        # Imágenes post-incendio (2 por página)
        if post_fire_images:
            pdf.add_page()
            pdf.set_font('Arial', 'B', 14)
            pdf.set_text_color(*COLORS["SECONDARY"])
            pdf.cell(0, 10, 'Serie Temporal Post-Incendio', 0, 1, 'L')
            pdf.ln(5)
            
            for i, img in enumerate(post_fire_images):
                if i > 0 and i % 2 == 0:
                    pdf.add_page()
                
                self._add_image_to_pdf(pdf, img, width=180)
                pdf.ln(5)
        
        # === PÁGINA FINAL: VERIFICACIÓN ===
        
        pdf.add_page()
        pdf.set_font('Arial', 'B', 14)
        pdf.set_text_color(*COLORS["SECONDARY"])
        pdf.cell(0, 10, 'Verificación y Autenticidad', 0, 1, 'L')
        pdf.ln(10)
        
        # QR Code
        verification_url = f"https://forestguard.freedynamicdns.org/verify/{report_id}"
        qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_Q, box_size=6, border=4)
        qr.add_data(verification_url)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")
        
        # Guardar QR temporalmente
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            qr_img.save(tmp.name)
            pdf.image(tmp.name, x=80, y=pdf.get_y(), w=50)
            Path(tmp.name).unlink()
        
        pdf.set_y(pdf.get_y() + 55)
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(0, 6, 'Escanear QR para verificar autenticidad', 0, 1, 'C')
        
        pdf.ln(10)
        
        # Disclaimer legal
        pdf.set_fill_color(*COLORS["BG_LIGHT"])
        pdf.set_font('Arial', 'I', 9)
        pdf.set_text_color(*COLORS["TEXT"])
        
        disclaimer = (
            "Este reporte fue generado automáticamente por ForestGuard utilizando "
            "imágenes satelitales Sentinel-2 (ESA Copernicus) procesadas mediante "
            "Google Earth Engine. Los datos de detección de incendios provienen de "
            "NASA FIRMS (VIIRS/MODIS). Este documento es de carácter informativo y "
            "no reemplaza peritajes oficiales realizados por autoridades competentes."
        )
        
        pdf.multi_cell(0, 5, disclaimer, 0, 'J')
        
        pdf.ln(10)
        
        # Fuentes de datos
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(0, 6, 'Fuentes de Datos:', 0, 1, 'L')
        pdf.set_font('Arial', '', 9)
        pdf.cell(0, 5, '• Imágenes: Sentinel-2 L2A (10m resolución) - ESA Copernicus', 0, 1, 'L')
        pdf.cell(0, 5, '• Detección de incendios: NASA FIRMS (VIIRS 375m)', 0, 1, 'L')
        pdf.cell(0, 5, '• Índices de vegetación: NDVI calculado server-side en GEE', 0, 1, 'L')
        
        # Retornar bytes
        return bytes(pdf.output())
    
    def _add_image_to_pdf(
        self,
        pdf: FPDF,
        img: ImageEvidence,
        width: int = 180
    ):
        """Agrega una imagen con metadata al PDF."""
        
        if img.thumbnail_bytes:
            # Guardar temporalmente
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                tmp.write(img.thumbnail_bytes)
                tmp_path = tmp.name
            
            # Insertar imagen
            pdf.image(tmp_path, x=15, y=pdf.get_y(), w=width)
            Path(tmp_path).unlink()
            
            pdf.set_y(pdf.get_y() + width * 0.6)  # Aproximar altura
        
        # Metadata
        pdf.set_font('Arial', '', 9)
        pdf.set_text_color(*COLORS["TEXT_LIGHT"])
        
        label = "PRE-INCENDIO" if img.is_pre_fire else img.acquisition_date.strftime("%d/%m/%Y")
        meta_text = f"{label} | {img.vis_type} | Nubes: {img.cloud_cover:.0f}%"
        
        if img.ndvi_mean is not None:
            meta_text += f" | NDVI: {img.ndvi_mean:.2f}"
        
        pdf.cell(0, 5, meta_text, 0, 1, 'C')
    
    # =========================================================================
    # UC-02: PERITAJES JUDICIALES
    # =========================================================================
    
    def _generate_judicial_report(
        self,
        request: ReportRequest,
        report_id: str
    ) -> ReportResult:
        """Genera peritaje judicial forense."""
        
        # Estructura similar a historical pero con:
        # - Más detalle legal
        # - Cronología del evento
        # - Condiciones climáticas
        # - Sección de hallazgos clave
        
        # TODO: Implementar cuando se tenga climate_service
        raise NotImplementedError("Judicial reports coming in next iteration")
    
    # =========================================================================
    # UC-09: PAQUETES DE EVIDENCIA
    # =========================================================================
    
    def _generate_evidence_package(
        self,
        request: ReportRequest,
        report_id: str
    ) -> ReportResult:
        """Genera paquete de evidencia para denuncias ciudadanas."""
        
        # Estructura:
        # - PDF resumen
        # - ZIP con imágenes
        # - JSON con metadata
        
        # TODO: Implementar
        raise NotImplementedError("Evidence packages coming in next iteration")
    
    # =========================================================================
    # UTILIDADES
    # =========================================================================
    
    def _generate_report_id(self, report_type: ReportType) -> str:
        """Genera ID único para el reporte."""
        prefix = {
            ReportType.HISTORICAL: "RPT-HIST",
            ReportType.JUDICIAL: "RPT-JUD",
            ReportType.CITIZEN_EVIDENCE: "RPT-CIT",
            ReportType.RECOVERY_MONITORING: "RPT-REC",
            ReportType.CERTIFICATE: "CERT",
        }.get(report_type, "RPT")
        
        timestamp = datetime.now().strftime("%Y%m%d")
        unique = uuid.uuid4().hex[:6].upper()
        
        return f"{prefix}-{timestamp}-{unique}"
    
    def _create_verification_hash(self, content: bytes) -> str:
        """Crea hash SHA-256 del contenido."""
        return f"sha256:{hashlib.sha256(content).hexdigest()}"
    
    def _add_months(self, d: date, months: int) -> date:
        """Suma meses a una fecha."""
        new_month = d.month + months
        new_year = d.year + (new_month - 1) // 12
        new_month = ((new_month - 1) % 12) + 1
        try:
            return date(new_year, new_month, d.day)
        except ValueError:
            return date(new_year, new_month, 28)
    
    # =========================================================================
    # VERIFICACIÓN
    # =========================================================================
    
    def verify_report(self, report_id: str, expected_hash: str) -> Dict[str, Any]:
        """
        Verifica la autenticidad de un reporte.
        
        Args:
            report_id: ID del reporte
            expected_hash: Hash esperado (sha256:...)
            
        Returns:
            Dict con resultado de verificación
        """
        try:
            # Descargar PDF del storage
            key = f"reports/historical/{report_id}.pdf"  # Simplified
            pdf_bytes = self._storage.download_bytes(key, bucket="forestguard-reports")
            
            # Calcular hash actual
            actual_hash = self._create_verification_hash(pdf_bytes)
            
            is_valid = actual_hash == expected_hash
            
            return {
                "report_id": report_id,
                "is_valid": is_valid,
                "expected_hash": expected_hash,
                "actual_hash": actual_hash,
                "verified_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "report_id": report_id,
                "is_valid": False,
                "error": str(e)
            }
    
    # =========================================================================
    # HEALTH CHECK
    # =========================================================================
    
    def health_check(self) -> Dict[str, Any]:
        """Verifica estado del servicio."""
        
        gee_status = self._gee.health_check()
        storage_status = self._storage.health_check()
        
        all_healthy = (
            gee_status.get("status") == "healthy" and
            storage_status.get("status") == "healthy"
        )
        
        return {
            "service": "ERS",
            "status": "healthy" if all_healthy else "degraded",
            "pdf_generation": FPDF_AVAILABLE,
            "gee_status": gee_status.get("status"),
            "storage_status": storage_status.get("status"),
            "supported_report_types": [rt.value for rt in ReportType]
        }


# =============================================================================
# FACTORY FUNCTION
# =============================================================================

def get_ers_service() -> ERSService:
    """Factory function para dependency injection."""
    return ERSService()


# =============================================================================
# EJEMPLO DE USO
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    ers = ERSService()
    
    # Health check
    status = ers.health_check()
    print(f"ERS Status: {status}")
    
    if status["status"] == "healthy":
        # Ejemplo de solicitud de reporte histórico
        request = ReportRequest(
            report_type=ReportType.HISTORICAL,
            fire_event_id="test-uuid-123",
            protected_area_name="Parque Nacional Chaco",
            fire_date=date(2020, 8, 15),
            bbox={
                "west": -60.5,
                "south": -27.0,
                "east": -60.3,
                "north": -26.8
            },
            max_images=5,
            vis_types=["RGB", "NDVI"],
            include_pre_fire=True,
            post_fire_frequency="annual"
        )
        
        print(f"\nGenerating report...")
        result = ers.generate_report(request)
        
        print(f"\nReport Result:")
        print(f"  ID: {result.report_id}")
        print(f"  Status: {result.status.value}")
        print(f"  PDF URL: {result.pdf_url}")
        print(f"  Images: {len(result.images)}")
        print(f"  Hash: {result.verification_hash}")
