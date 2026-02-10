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
              Storage Service (object storage)

Autor: ForestGuard Dev Team
Versión: 1.0.0
Última actualización: 2025-01-29
"""

import hashlib
import json
import logging
import tempfile
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from enum import Enum
from io import BytesIO
from pathlib import Path
from typing import Any, BinaryIO, Dict, List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

# PDF generation
try:
    import qrcode
    from fpdf import FPDF

    FPDF_AVAILABLE = True
except ImportError:
    FPDF_AVAILABLE = False
    FPDF = object
    qrcode = None
    logging.warning("fpdf2 or qrcode not installed. PDF generation disabled.")

from app.services.report_pdf_service import add_verification_block

# Importar servicios
try:
    from .gee_service import GEEImageNotFoundError, GEEService, ImageMetadata
    from .storage_service import StorageService, UploadResult
    from .vae_service import RecoveryAnalysis, TemporalAnalysis, VAEService
except ImportError:
    from gee_service import GEEImageNotFoundError, GEEService, ImageMetadata
    from storage_service import StorageService, UploadResult
    from vae_service import RecoveryAnalysis, TemporalAnalysis, VAEService

logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURACIÓN
# =============================================================================

# Colores corporativos
COLORS = {
    "PRIMARY": (46, 125, 50),  # Verde Forestal
    "SECONDARY": (27, 94, 32),  # Verde Oscuro
    "ACCENT": (200, 83, 0),  # Naranja
    "DANGER": (200, 0, 0),  # Rojo
    "TEXT": (50, 50, 50),  # Gris Oscuro
    "TEXT_LIGHT": (128, 128, 128),  # Gris
    "BG_LIGHT": (245, 245, 245),  # Gris Muy Claro
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

    HISTORICAL = "historical"  # UC-12
    JUDICIAL = "judicial"  # UC-02
    CITIZEN_EVIDENCE = "citizen_evidence"  # UC-09
    RECOVERY_MONITORING = "recovery"  # UC-06
    CERTIFICATE = "certificate"  # UC-07


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
    include_monthly_images: bool = True
    include_climate: bool = True
    include_imagery: bool = True
    language: str = "es"

    # Spatial
    bbox: Optional[Dict[str, float]] = None

    # Output
    output_format: str = "hybrid"  # pdf, web, hybrid

    # Requester
    requester_email: Optional[str] = None
    requester_name: Optional[str] = None
    requester_id: Optional[str] = None
    case_reference: Optional[str] = None


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
    gee_system_index: Optional[str] = None
    visualization_params: Optional[Dict[str, Any]] = None
    acquisition_time: Optional[time] = None


@dataclass
class FireEventSnapshot:
    """Snapshot de un evento de incendio para reporte judicial."""

    id: str
    start_date: datetime
    end_date: datetime
    total_detections: int
    avg_frp: Optional[float]
    max_frp: Optional[float]
    sum_frp: Optional[float]
    avg_confidence: Optional[float]
    estimated_area_hectares: Optional[float]
    province: Optional[str]
    department: Optional[str]
    centroid_lon: Optional[float]
    centroid_lat: Optional[float]


@dataclass
class DetectionSnapshot:
    """Detalle de detección para cronología."""

    detected_at: datetime
    latitude: Optional[float]
    longitude: Optional[float]
    fire_radiative_power: Optional[float]
    confidence: Optional[int]


@dataclass
class ClimateSnapshot:
    """Resumen climático asociado a un evento."""

    reference_date: date
    temp_max_celsius: Optional[float]
    temp_min_celsius: Optional[float]
    temp_mean_celsius: Optional[float]
    wind_speed_kmh: Optional[float]
    wind_direction_degrees: Optional[int]
    wind_gusts_kmh: Optional[float]
    precipitation_mm: Optional[float]
    relative_humidity_pct: Optional[int]
    kbdi: Optional[float]
    data_source: Optional[str]


def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


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
        self.rect(0, 0, 210, 30, "F")

        # Logo (si existe)
        offset_x = 10
        if LOGO_PATH.exists():
            try:
                self.image(str(LOGO_PATH), 10, 5, 20)
                offset_x = 35
            except:
                pass

        # Título
        self.set_font("Arial", "B", 16)
        self.set_text_color(*COLORS["WHITE"])
        self.set_xy(offset_x, 8)
        self.cell(0, 8, "ForestGuard", 0, 1, "L")

        # Subtítulo según tipo
        subtitles = {
            ReportType.HISTORICAL: "Reporte Histórico de Incendios",
            ReportType.JUDICIAL: "Peritaje Judicial Forense",
            ReportType.CITIZEN_EVIDENCE: "Paquete de Evidencia",
            ReportType.RECOVERY_MONITORING: "Monitoreo de Recuperación",
            ReportType.CERTIFICATE: "Certificado Legal",
        }

        self.set_font("Arial", "", 10)
        self.set_xy(offset_x, 16)
        self.cell(0, 6, subtitles.get(self.report_type, "Reporte"), 0, 1, "L")

        self.ln(15)

    def footer(self):
        """Pie de página con verificación."""
        self.set_y(-20)

        # Línea separadora
        self.set_draw_color(*COLORS["PRIMARY"])
        self.line(10, 280, 200, 280)

        # Texto
        self.set_font("Arial", "I", 8)
        self.set_text_color(*COLORS["TEXT_LIGHT"])

        self.set_y(-15)
        self.cell(0, 5, f"ID: {self.report_id}", 0, 1, "L")
        self.cell(
            0,
            5,
            f'Página {self.page_no()}/{{nb}} | Generado: {datetime.now().strftime("%Y-%m-%d %H:%M")} | forestguard.freedynamicdns.org',
            0,
            0,
            "C",
        )


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
        db: Optional[Session] = None,
        gee_service: Optional[GEEService] = None,
        vae_service: Optional[VAEService] = None,
        storage_service: Optional[StorageService] = None,
    ):
        """Inicializa el servicio ERS."""
        self._db = db
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
                error_message=str(e),
            )

    # =========================================================================
    # UC-12: REPORTES HISTÓRICOS
    # =========================================================================

    def _generate_historical_report(
        self, request: ReportRequest, report_id: str
    ) -> ReportResult:
        """Genera reporte histórico de incendios en área protegida."""
        if (
            request.protected_area_id
            or request.protected_area_name
            or request.date_range_start
            or request.date_range_end
        ):
            return self._generate_ucf11_historical_report(request, report_id)

        self._gee.authenticate()

        if not request.bbox or not request.fire_date:
            raise ValueError("bbox and fire_date are required for historical reports")

        # 1. Obtener análisis temporal
        max_images = min(self._resolve_report_max_images(), request.max_images or 12)
        analysis = self._vae.analyze_temporal_series(
            fire_event_id=request.fire_event_id or "unknown",
            bbox=request.bbox,
            fire_date=request.fire_date,
            protected_area_name=request.protected_area_name or "Área Protegida",
            years_to_analyze=min(10, max_images),
        )

        # 2. Recolectar imágenes
        images = self._collect_images_for_report(
            bbox=request.bbox,
            fire_date=request.fire_date,
            max_images=max_images,
            vis_types=request.vis_types,
            include_pre_fire=request.include_pre_fire,
            frequency=request.post_fire_frequency,
        )

        # 3. Generar PDF
        pdf_bytes = self._create_historical_pdf(
            report_id=report_id, request=request, analysis=analysis, images=images
        )

        # 4. Calcular hash de verificación
        verification_hash = self._create_verification_hash(pdf_bytes)

        # 5. Subir a storage
        pdf_result = self._storage.upload_report_pdf(
            report_id=report_id, pdf_bytes=pdf_bytes, report_type="historical"
        )

        # 6. Subir thumbnails a storage
        for img in images:
            if img.thumbnail_bytes:
                self._storage.upload_thumbnail(
                    fire_event_id=request.fire_event_id or report_id,
                    image_bytes=img.thumbnail_bytes,
                    vis_type=img.vis_type,
                    acquisition_date=img.acquisition_date,
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
            total_affected_hectares=0,  # TODO: calcular desde análisis
        )

    def _generate_ucf11_historical_report(
        self,
        request: ReportRequest,
        report_id: str,
    ) -> ReportResult:
        if self._db is None:
            raise ValueError("DB session is required for historical reports")

        if not request.date_range_start or not request.date_range_end:
            raise ValueError("date_range_start and date_range_end are required")

        if request.date_range_end < request.date_range_start:
            raise ValueError("end_date must be after start_date")

        area = self._fetch_protected_area(
            request.protected_area_id, request.protected_area_name
        )
        if not area:
            raise ValueError("Protected area not found")

        area_id, area_name = area
        stats = self._fetch_fire_event_stats(
            area_id, request.date_range_start, request.date_range_end
        )
        max_images = self._resolve_report_max_images()
        images = self._fetch_historical_images(
            area_id=area_id,
            start_date=request.date_range_start,
            end_date=request.date_range_end,
            limit=max_images,
            include_monthly=request.include_monthly_images,
        )

        generated_at = datetime.now()
        pdf_bytes = self._create_ucf11_historical_pdf(
            report_id=report_id,
            area_name=area_name,
            start_date=request.date_range_start,
            end_date=request.date_range_end,
            images=images,
            stats=stats,
            generated_at=generated_at,
        )

        verification_hash = self._create_verification_hash(pdf_bytes)
        pdf_result = self._storage.upload_report_pdf(
            report_id=report_id,
            pdf_bytes=pdf_bytes,
            report_type="historical",
        )

        self._record_report_audit(
            report_id=report_id,
            request=request,
            verification_hash=verification_hash,
            pdf_url=pdf_result.url if pdf_result.success else None,
            images=images,
            generated_at=generated_at,
            report_type="historical",
            resource_type="protected_area",
            resource_id=area_id,
            extra_details={
                "protected_area_name": area_name,
                "date_range_start": request.date_range_start.isoformat(),
                "date_range_end": request.date_range_end.isoformat(),
                "fires_included": stats.get("total_fires", 0),
            },
        )

        return ReportResult(
            report_id=report_id,
            report_type=ReportType.HISTORICAL,
            status=ReportStatus.COMPLETED,
            pdf_url=pdf_result.url if pdf_result.success else None,
            web_viewer_url=f"https://forestguard.freedynamicdns.org/viewer/{report_id}",
            images=images,
            verification_hash=verification_hash,
            verification_url=f"https://forestguard.freedynamicdns.org/verify/{report_id}",
            fire_events_found=stats.get("total_fires", 0),
            total_affected_hectares=0,
        )

    def _fetch_protected_area(
        self,
        area_id: Optional[str],
        area_name: Optional[str],
    ) -> Optional[tuple[str, str]]:
        if self._db is None:
            return None
        if area_id:
            row = (
                self._db.execute(
                    text(
                        "SELECT id, official_name FROM protected_areas WHERE id = :id"
                    ),
                    {"id": area_id},
                )
                .mappings()
                .first()
            )
            if row:
                return (str(row["id"]), row["official_name"])

        if area_name:
            row = (
                self._db.execute(
                    text(
                        """
                        SELECT id, official_name
                          FROM protected_areas
                         WHERE official_name ILIKE :name
                            OR :alt_name = ANY(alternative_names)
                         LIMIT 1
                        """
                    ),
                    {"name": f"%{area_name}%", "alt_name": area_name},
                )
                .mappings()
                .first()
            )
            if row:
                return (str(row["id"]), row["official_name"])
        return None

    def _fetch_fire_event_stats(
        self,
        area_id: str,
        start_date: date,
        end_date: date,
    ) -> Dict[str, Any]:
        if self._db is None:
            return {"total_fires": 0}
        row = (
            self._db.execute(
                text(
                    """
                    SELECT COUNT(*) AS total_fires,
                           MIN(fire_date) AS earliest_fire,
                           MAX(fire_date) AS latest_fire
                      FROM fire_protected_area_intersections
                     WHERE protected_area_id = :area_id
                       AND fire_date BETWEEN :start_date AND :end_date
                    """
                ),
                {"area_id": area_id, "start_date": start_date, "end_date": end_date},
            )
            .mappings()
            .first()
        )
        if not row:
            return {"total_fires": 0}
        return {
            "total_fires": int(row.get("total_fires") or 0),
            "earliest_fire": row.get("earliest_fire"),
            "latest_fire": row.get("latest_fire"),
        }

    def _fetch_historical_images(
        self,
        area_id: str,
        start_date: date,
        end_date: date,
        limit: int,
        include_monthly: bool,
    ) -> List[ImageEvidence]:
        if self._db is None:
            return []
        filters = """
            fpa.protected_area_id = :area_id
            AND si.acquisition_date BETWEEN :start_date AND :end_date
            AND (si.image_type IS NULL OR si.image_type <> 'pre_fire')
            AND (si.days_after_fire IS NULL OR si.days_after_fire >= 0)
        """
        if not include_monthly:
            filters += (
                " AND (si.image_type IS NULL OR si.image_type <> 'monthly_monitoring')"
            )

        query = text(
            f"""
            SELECT si.acquisition_date,
                   si.acquisition_time,
                   si.image_type,
                   si.cloud_cover_pct,
                   si.r2_url,
                   si.thumbnail_url,
                   si.gee_system_index,
                   si.visualization_params,
                   si.satellite
              FROM satellite_images si
              JOIN fire_protected_area_intersections fpa
                ON fpa.fire_event_id = si.fire_event_id
             WHERE {filters}
             ORDER BY si.acquisition_date ASC NULLS LAST
             LIMIT :limit
            """
        )
        rows = (
            self._db.execute(
                query,
                {
                    "area_id": area_id,
                    "start_date": start_date,
                    "end_date": end_date,
                    "limit": limit,
                },
            )
            .mappings()
            .all()
        )
        images: List[ImageEvidence] = []
        for row in rows:
            vis_params = row.get("visualization_params")
            if isinstance(vis_params, str):
                try:
                    vis_params = json.loads(vis_params)
                except json.JSONDecodeError:
                    vis_params = None
            vis_type = self._infer_vis_type(row.get("image_type") or "", vis_params)
            images.append(
                ImageEvidence(
                    image_id=row.get("gee_system_index") or "unknown",
                    acquisition_date=row.get("acquisition_date") or date.today(),
                    acquisition_time=row.get("acquisition_time"),
                    vis_type=vis_type,
                    thumbnail_url=row.get("thumbnail_url") or row.get("r2_url") or "",
                    hd_url=row.get("r2_url"),
                    cloud_cover=_to_float(row.get("cloud_cover_pct")) or 0,
                    satellite=row.get("satellite") or "Sentinel-2",
                    gee_system_index=row.get("gee_system_index"),
                    visualization_params=vis_params,
                )
            )
        return images

    def _create_ucf11_historical_pdf(
        self,
        report_id: str,
        area_name: str,
        start_date: date,
        end_date: date,
        images: List[ImageEvidence],
        stats: Dict[str, Any],
        generated_at: datetime,
    ) -> bytes:
        if not FPDF_AVAILABLE:
            raise RuntimeError("fpdf2 not installed")

        pdf = ForestGuardReportPDF(report_type=ReportType.HISTORICAL)
        pdf.report_id = report_id
        pdf.alias_nb_pages()
        pdf.add_page()

        pdf.set_font("Arial", "B", 18)
        pdf.set_text_color(*COLORS["SECONDARY"])
        pdf.cell(0, 10, "REPORTE HISTÓRICO DE INCENDIOS", 0, 1, "C")
        pdf.ln(4)

        pdf.set_font("Courier", "B", 12)
        pdf.set_text_color(*COLORS["ACCENT"])
        pdf.cell(0, 8, f"REF: {report_id}", 0, 1, "C")
        pdf.ln(6)

        pdf.set_fill_color(*COLORS["BG_LIGHT"])
        pdf.rect(10, pdf.get_y(), 190, 40, "F")
        pdf.set_y(pdf.get_y() + 4)
        pdf.set_font("Arial", "B", 10)
        pdf.set_text_color(*COLORS["TEXT"])

        total_fires = stats.get("total_fires", 0)
        cost_per_image = self._resolve_report_image_cost()
        total_cost = cost_per_image * len(images)

        info_items = [
            ("Área protegida:", area_name),
            (
                "Rango:",
                f"{start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')}",
            ),
            ("Incendios incluidos:", str(total_fires)),
            (
                "Imágenes incluidas:",
                f"{len(images)} / {self._resolve_report_max_images()}",
            ),
            ("Costo por imagen (USD):", f"{cost_per_image:.2f}"),
            ("Costo total (USD):", f"{total_cost:.2f}"),
        ]

        for label, value in info_items:
            pdf.set_x(15)
            pdf.cell(50, 6, label, 0, 0)
            pdf.set_font("Arial", "", 10)
            pdf.cell(0, 6, value, 0, 1)
            pdf.set_font("Arial", "B", 10)

        pdf.ln(6)
        pdf.set_font("Arial", "B", 12)
        pdf.set_text_color(*COLORS["SECONDARY"])
        pdf.cell(0, 8, "Serie post-incendio", 0, 1, "L")
        pdf.set_font("Arial", "", 10)
        pdf.set_text_color(*COLORS["TEXT"])

        if not images:
            pdf.multi_cell(
                0,
                5,
                "No se encontraron imágenes post-incendio para el rango indicado. "
                "El reporte se emite con esta salvedad.",
                0,
                "J",
            )
        else:
            for idx, img in enumerate(images):
                if idx > 0 and idx % 2 == 0:
                    pdf.add_page()
                self._add_image_to_pdf(pdf, img, width=180)
                pdf.ln(5)

        pdf.add_page()
        verification_url = f"https://forestguard.freedynamicdns.org/verify/{report_id}"
        add_verification_block(
            pdf,
            verification_url=verification_url,
            title="Verificacion y Autenticidad",
        )
        pdf.ln(8)

        pdf.set_font("Arial", "I", 9)
        pdf.set_text_color(*COLORS["TEXT"])
        pdf.multi_cell(
            0,
            5,
            "Este reporte fue generado automáticamente por ForestGuard. "
            "El hash SHA-256 del PDF se almacena en la base de datos para verificación. "
            "Imágenes satelitales Sentinel-2 procesadas vía Google Earth Engine.",
            0,
            "J",
        )

        pdf.set_font("Arial", "", 8)
        pdf.cell(
            0, 5, f"Generado: {generated_at.strftime('%d/%m/%Y %H:%M')}", 0, 1, "L"
        )

        return bytes(pdf.output())

    def _collect_images_for_report(
        self,
        bbox: Dict[str, float],
        fire_date: date,
        max_images: int,
        vis_types: List[str],
        include_pre_fire: bool,
        frequency: str,
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
                    is_pre_fire=True,
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
                target = date(
                    fire_date.year + year_offset,
                    fire_date.month,
                    min(fire_date.day, 28),
                )
                if target > date.today():
                    break

                try:
                    img = self._get_image_evidence(
                        bbox=bbox, target_date=target, vis_type="RGB"
                    )
                    if img:
                        images.append(img)

                        # También NDVI si está en vis_types
                        if "NDVI" in vis_types:
                            ndvi_img = self._get_image_evidence(
                                bbox=bbox, target_date=target, vis_type="NDVI"
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
                        bbox=bbox, target_date=target, vis_type="RGB"
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
        is_pre_fire: bool = False,
    ) -> Optional[ImageEvidence]:
        """Obtiene evidencia de imagen para una fecha."""

        # Ventana de búsqueda
        start = target_date - timedelta(days=30)
        end = target_date + timedelta(days=30)

        collection = self._gee.get_sentinel_collection(
            bbox=bbox, start_date=start, end_date=end, max_cloud_cover=30
        )

        image = self._gee.get_best_image(collection, target_date=target_date)
        metadata = self._gee.get_image_metadata(image)

        # Obtener thumbnail
        thumb_url = self._gee.get_thumbnail_url(
            image, bbox, vis_type=vis_type, dimensions=512
        )
        thumb_bytes = self._gee.download_thumbnail(
            image, bbox, vis_type=vis_type, dimensions=512
        )

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
            is_pre_fire=is_pre_fire,
        )

    def _create_historical_pdf(
        self,
        report_id: str,
        request: ReportRequest,
        analysis: TemporalAnalysis,
        images: List[ImageEvidence],
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
        pdf.set_font("Arial", "B", 18)
        pdf.set_text_color(*COLORS["SECONDARY"])
        pdf.cell(0, 10, "REPORTE HISTÓRICO DE INCENDIOS", 0, 1, "C")
        pdf.ln(5)

        # Número de reporte
        pdf.set_font("Courier", "B", 12)
        pdf.set_text_color(*COLORS["ACCENT"])
        pdf.cell(0, 8, f"REF: {report_id}", 0, 1, "C")
        pdf.ln(10)

        # Información del área
        pdf.set_fill_color(*COLORS["BG_LIGHT"])
        pdf.rect(10, pdf.get_y(), 190, 40, "F")

        pdf.set_y(pdf.get_y() + 5)
        pdf.set_font("Arial", "B", 11)
        pdf.set_text_color(*COLORS["TEXT"])

        info_items = [
            ("Área Protegida:", request.protected_area_name or "No especificada"),
            ("Fecha del Incendio:", analysis.fire_date.strftime("%d/%m/%Y")),
            (
                "Período Analizado:",
                f"{analysis.analysis_period[0].strftime('%d/%m/%Y')} - {analysis.analysis_period[1].strftime('%d/%m/%Y')}",
            ),
            ("Imágenes Analizadas:", str(analysis.total_images_analyzed)),
        ]

        for label, value in info_items:
            pdf.set_x(15)
            pdf.set_font("Arial", "B", 10)
            pdf.cell(45, 8, label, 0, 0)
            pdf.set_font("Arial", "", 10)
            pdf.cell(0, 8, value, 0, 1)

        pdf.ln(15)

        # Estado de recuperación
        pdf.set_font("Arial", "B", 14)
        pdf.set_text_color(*COLORS["SECONDARY"])
        pdf.cell(0, 10, "Estado de Recuperación", 0, 1, "L")

        # Box de estado
        status_color = (
            COLORS["PRIMARY"]
            if analysis.overall_recovery_percentage > 70
            else COLORS["ACCENT"]
        )
        if analysis.overall_recovery_percentage < 40:
            status_color = COLORS["DANGER"]

        pdf.set_fill_color(*status_color)
        pdf.set_text_color(*COLORS["WHITE"])
        pdf.set_font("Arial", "B", 24)
        pdf.set_x(60)
        pdf.cell(
            90, 20, f"{analysis.overall_recovery_percentage:.0f}%", 1, 1, "C", True
        )

        pdf.set_text_color(*COLORS["TEXT"])
        pdf.set_font("Arial", "", 10)
        pdf.cell(
            0,
            8,
            f'Estado: {analysis.final_recovery_status.value.replace("_", " ").title()}',
            0,
            1,
            "C",
        )
        pdf.cell(
            0,
            8,
            f"Tendencia: {analysis.recovery_trend.title()} (confianza: {analysis.trend_confidence:.0%})",
            0,
            1,
            "C",
        )

        if analysis.images_with_anomalies > 0:
            pdf.set_text_color(*COLORS["DANGER"])
            pdf.set_font("Arial", "B", 10)
            pdf.cell(
                0,
                8,
                f"⚠ Anomalías detectadas: {analysis.images_with_anomalies}",
                0,
                1,
                "C",
            )

        pdf.ln(10)

        # === PÁGINAS DE IMÁGENES ===

        # Separar pre-fire y post-fire
        pre_fire_images = [img for img in images if img.is_pre_fire]
        post_fire_images = [img for img in images if not img.is_pre_fire]

        # Imagen pre-incendio
        if pre_fire_images:
            pdf.add_page()
            pdf.set_font("Arial", "B", 14)
            pdf.set_text_color(*COLORS["SECONDARY"])
            pdf.cell(0, 10, "Imagen Pre-Incendio (Baseline)", 0, 1, "L")
            pdf.ln(5)

            img = pre_fire_images[0]
            self._add_image_to_pdf(pdf, img, width=180)

        # Imágenes post-incendio (2 por página)
        if post_fire_images:
            pdf.add_page()
            pdf.set_font("Arial", "B", 14)
            pdf.set_text_color(*COLORS["SECONDARY"])
            pdf.cell(0, 10, "Serie Temporal Post-Incendio", 0, 1, "L")
            pdf.ln(5)

            for i, img in enumerate(post_fire_images):
                if i > 0 and i % 2 == 0:
                    pdf.add_page()

                self._add_image_to_pdf(pdf, img, width=180)
                pdf.ln(5)

        # === PÁGINA FINAL: VERIFICACIÓN ===

        pdf.add_page()
        verification_url = f"https://forestguard.freedynamicdns.org/verify/{report_id}"
        add_verification_block(
            pdf,
            verification_url=verification_url,
            title="Verificacion y Autenticidad",
        )

        pdf.ln(10)

        # Disclaimer legal
        pdf.set_fill_color(*COLORS["BG_LIGHT"])
        pdf.set_font("Arial", "I", 9)
        pdf.set_text_color(*COLORS["TEXT"])

        disclaimer = (
            "Este reporte fue generado automáticamente por ForestGuard utilizando "
            "imágenes satelitales Sentinel-2 (ESA Copernicus) procesadas mediante "
            "Google Earth Engine. Los datos de detección de incendios provienen de "
            "NASA FIRMS (VIIRS/MODIS). Este documento es de carácter informativo y "
            "no reemplaza peritajes oficiales realizados por autoridades competentes."
        )

        pdf.multi_cell(0, 5, disclaimer, 0, "J")

        pdf.ln(10)

        # Fuentes de datos
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 6, "Fuentes de Datos:", 0, 1, "L")
        pdf.set_font("Arial", "", 9)
        pdf.cell(
            0,
            5,
            "• Imágenes: Sentinel-2 L2A (10m resolución) - ESA Copernicus",
            0,
            1,
            "L",
        )
        pdf.cell(0, 5, "• Detección de incendios: NASA FIRMS (VIIRS 375m)", 0, 1, "L")
        pdf.cell(
            0,
            5,
            "• Índices de vegetación: NDVI calculado server-side en GEE",
            0,
            1,
            "L",
        )

        # Retornar bytes
        return bytes(pdf.output())

    def _add_image_to_pdf(self, pdf: FPDF, img: ImageEvidence, width: int = 180):
        """Agrega una imagen con metadata al PDF."""

        if img.thumbnail_bytes:
            # Guardar temporalmente
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                tmp.write(img.thumbnail_bytes)
                tmp_path = tmp.name

            # Insertar imagen
            pdf.image(tmp_path, x=15, y=pdf.get_y(), w=width)
            Path(tmp_path).unlink()

            pdf.set_y(pdf.get_y() + width * 0.6)  # Aproximar altura

        # Metadata
        pdf.set_font("Arial", "", 9)
        pdf.set_text_color(*COLORS["TEXT_LIGHT"])

        label = (
            "PRE-INCENDIO"
            if img.is_pre_fire
            else img.acquisition_date.strftime("%d/%m/%Y")
        )
        meta_text = f"{label} | {img.vis_type} | Nubes: {img.cloud_cover:.0f}%"

        if img.ndvi_mean is not None:
            meta_text += f" | NDVI: {img.ndvi_mean:.2f}"

        pdf.cell(0, 5, meta_text, 0, 1, "C")

    # =========================================================================
    # UC-02: PERITAJES JUDICIALES
    # =========================================================================

    def _generate_judicial_report(
        self, request: ReportRequest, report_id: str
    ) -> ReportResult:
        """Genera peritaje judicial forense."""
        if not request.fire_event_id:
            raise ValueError("fire_event_id is required for judicial reports")
        if self._db is None:
            raise ValueError("DB session is required for judicial reports")

        self._gee.authenticate()

        fire = self._fetch_fire_event_snapshot(request.fire_event_id)
        if not fire:
            raise ValueError(f"Fire event not found: {request.fire_event_id}")

        detections = self._fetch_fire_detections(request.fire_event_id)
        climate = (
            self._fetch_climate_snapshot(request.fire_event_id)
            if request.include_climate
            else None
        )

        max_images = self._resolve_report_max_images()
        if request.max_images:
            max_images = min(max_images, request.max_images)
        images: List[ImageEvidence] = []
        if request.include_imagery and max_images > 0:
            images = self._fetch_satellite_images(request.fire_event_id, max_images)

        generated_at = datetime.now()
        pdf_bytes = self._create_judicial_pdf(
            report_id=report_id,
            request=request,
            fire=fire,
            detections=detections,
            climate=climate,
            images=images,
            generated_at=generated_at,
        )

        verification_hash = self._create_verification_hash(pdf_bytes)
        pdf_result = self._storage.upload_report_pdf(
            report_id=report_id,
            pdf_bytes=pdf_bytes,
            report_type="judicial",
        )

        self._record_report_audit(
            report_id=report_id,
            request=request,
            verification_hash=verification_hash,
            pdf_url=pdf_result.url if pdf_result.success else None,
            images=images,
            generated_at=generated_at,
            report_type="judicial",
            resource_type="fire_event",
            resource_id=fire.id,
            extra_details={
                "fire_event_id": fire.id,
                "case_reference": request.case_reference,
                "has_climate": climate is not None,
            },
        )

        return ReportResult(
            report_id=report_id,
            report_type=ReportType.JUDICIAL,
            status=ReportStatus.COMPLETED,
            pdf_url=pdf_result.url if pdf_result.success else None,
            web_viewer_url=f"https://forestguard.freedynamicdns.org/viewer/{report_id}",
            images=images,
            verification_hash=verification_hash,
            verification_url=f"https://forestguard.freedynamicdns.org/verify/{report_id}",
            fire_events_found=1,
            total_affected_hectares=float(fire.estimated_area_hectares or 0),
        )

    def _get_system_param(self, key: str) -> Optional[object]:
        if self._db is None:
            return None
        try:
            row = (
                self._db.execute(
                    text(
                        "SELECT param_value FROM system_parameters WHERE param_key = :key"
                    ),
                    {"key": key},
                )
                .mappings()
                .first()
            )
        except SQLAlchemyError as exc:
            logger.warning("system_parameters lookup failed for %s: %s", key, exc)
            self._db.rollback()
            return None
        if not row:
            return None
        return row.get("param_value")

    def _resolve_report_max_images(self, default: int = 12) -> int:
        value = self._get_system_param("report_max_images")
        if isinstance(value, dict) and "value" in value:
            try:
                return int(value["value"])
            except (TypeError, ValueError):
                return default
        if isinstance(value, (int, float)):
            return int(value)
        return default

    def _resolve_report_image_cost(self, default: float = 0.5) -> float:
        value = self._get_system_param("report_image_cost_usd")
        if isinstance(value, dict) and "value" in value:
            try:
                return float(value["value"])
            except (TypeError, ValueError):
                return default
        if isinstance(value, (int, float)):
            return float(value)
        return default

    def _fetch_fire_event_snapshot(
        self, fire_event_id: str
    ) -> Optional[FireEventSnapshot]:
        if self._db is None:
            return None
        row = (
            self._db.execute(
                text(
                    """
                    SELECT fe.id,
                           fe.start_date,
                           fe.end_date,
                           fe.total_detections,
                           fe.avg_frp,
                           fe.max_frp,
                           fe.sum_frp,
                           fe.avg_confidence,
                           fe.estimated_area_hectares,
                           fe.province,
                           fe.department,
                           ST_X(fe.centroid::geometry) AS lon,
                           ST_Y(fe.centroid::geometry) AS lat
                      FROM fire_events fe
                     WHERE fe.id = :fire_id
                    """
                ),
                {"fire_id": fire_event_id},
            )
            .mappings()
            .first()
        )
        if not row:
            return None
        return FireEventSnapshot(
            id=str(row["id"]),
            start_date=row["start_date"],
            end_date=row["end_date"],
            total_detections=int(row["total_detections"] or 0),
            avg_frp=_to_float(row.get("avg_frp")),
            max_frp=_to_float(row.get("max_frp")),
            sum_frp=_to_float(row.get("sum_frp")),
            avg_confidence=_to_float(row.get("avg_confidence")),
            estimated_area_hectares=_to_float(row.get("estimated_area_hectares")),
            province=row.get("province"),
            department=row.get("department"),
            centroid_lon=_to_float(row.get("lon")),
            centroid_lat=_to_float(row.get("lat")),
        )

    def _fetch_fire_detections(self, fire_event_id: str) -> List[DetectionSnapshot]:
        if self._db is None:
            return []
        rows = (
            self._db.execute(
                text(
                    """
                    SELECT detected_at,
                           latitude,
                           longitude,
                           fire_radiative_power,
                           confidence_normalized
                      FROM fire_detections
                     WHERE fire_event_id = :fire_id
                     ORDER BY detected_at ASC
                    """
                ),
                {"fire_id": fire_event_id},
            )
            .mappings()
            .all()
        )
        detections: List[DetectionSnapshot] = []
        for row in rows:
            detections.append(
                DetectionSnapshot(
                    detected_at=row["detected_at"],
                    latitude=_to_float(row.get("latitude")),
                    longitude=_to_float(row.get("longitude")),
                    fire_radiative_power=_to_float(row.get("fire_radiative_power")),
                    confidence=_to_int(row.get("confidence_normalized")),
                )
            )
        return detections

    def _fetch_climate_snapshot(self, fire_event_id: str) -> Optional[ClimateSnapshot]:
        if self._db is None:
            return None
        row = (
            self._db.execute(
                text(
                    """
                    SELECT cd.reference_date,
                           cd.temp_max_celsius,
                           cd.temp_min_celsius,
                           cd.temp_mean_celsius,
                           cd.wind_speed_kmh,
                           cd.wind_direction_degrees,
                           cd.wind_gusts_kmh,
                           cd.precipitation_mm,
                           cd.relative_humidity_pct,
                           cd.kbdi,
                           cd.data_source
                      FROM fire_climate_associations fca
                      JOIN climate_data cd
                        ON cd.id = fca.climate_data_id
                     WHERE fca.fire_event_id = :fire_id
                     ORDER BY cd.reference_date DESC
                     LIMIT 1
                    """
                ),
                {"fire_id": fire_event_id},
            )
            .mappings()
            .first()
        )
        if not row:
            return None
        return ClimateSnapshot(
            reference_date=row["reference_date"],
            temp_max_celsius=_to_float(row.get("temp_max_celsius")),
            temp_min_celsius=_to_float(row.get("temp_min_celsius")),
            temp_mean_celsius=_to_float(row.get("temp_mean_celsius")),
            wind_speed_kmh=_to_float(row.get("wind_speed_kmh")),
            wind_direction_degrees=_to_int(row.get("wind_direction_degrees")),
            wind_gusts_kmh=_to_float(row.get("wind_gusts_kmh")),
            precipitation_mm=_to_float(row.get("precipitation_mm")),
            relative_humidity_pct=_to_int(row.get("relative_humidity_pct")),
            kbdi=_to_float(row.get("kbdi")),
            data_source=row.get("data_source"),
        )

    def _fetch_satellite_images(
        self, fire_event_id: str, limit: int
    ) -> List[ImageEvidence]:
        if self._db is None:
            return []
        rows = (
            self._db.execute(
                text(
                    """
                    SELECT acquisition_date,
                           acquisition_time,
                           image_type,
                           cloud_cover_pct,
                           r2_url,
                           thumbnail_url,
                           gee_system_index,
                           visualization_params,
                           bands_included,
                           satellite
                      FROM satellite_images
                     WHERE fire_event_id = :fire_id
                     ORDER BY acquisition_date DESC NULLS LAST
                     LIMIT :limit
                    """
                ),
                {"fire_id": fire_event_id, "limit": limit},
            )
            .mappings()
            .all()
        )
        images: List[ImageEvidence] = []
        for row in rows:
            vis_params = row.get("visualization_params")
            if isinstance(vis_params, str):
                try:
                    vis_params = json.loads(vis_params)
                except json.JSONDecodeError:
                    vis_params = None
            image_type = row.get("image_type") or ""
            vis_type = self._infer_vis_type(image_type, vis_params)
            images.append(
                ImageEvidence(
                    image_id=row.get("gee_system_index") or "unknown",
                    acquisition_date=row.get("acquisition_date") or date.today(),
                    vis_type=vis_type,
                    thumbnail_url=row.get("thumbnail_url") or row.get("r2_url") or "",
                    thumbnail_bytes=None,
                    hd_url=row.get("r2_url"),
                    cloud_cover=_to_float(row.get("cloud_cover_pct")) or 0,
                    satellite=row.get("satellite") or "Sentinel-2",
                    gee_system_index=row.get("gee_system_index"),
                    visualization_params=vis_params,
                    acquisition_time=row.get("acquisition_time"),
                )
            )
        return images

    @staticmethod
    def _infer_vis_type(image_type: str, vis_params: Optional[Dict[str, Any]]) -> str:
        image_type = (image_type or "").lower()
        if "dnbr" in image_type:
            return "DNBR"
        if "nbr" in image_type:
            return "NBR"
        if isinstance(vis_params, dict):
            if "vis_type" in vis_params:
                return str(vis_params["vis_type"]).upper()
            bands = vis_params.get("bands")
            if isinstance(bands, list) and len(bands) == 3:
                if [b.upper() for b in bands] == ["B12", "B8A", "B4"]:
                    return "NBR"
        return "RGB"

    def _create_judicial_pdf(
        self,
        report_id: str,
        request: ReportRequest,
        fire: FireEventSnapshot,
        detections: List[DetectionSnapshot],
        climate: Optional[ClimateSnapshot],
        images: List[ImageEvidence],
        generated_at: datetime,
    ) -> bytes:
        if not FPDF_AVAILABLE:
            raise RuntimeError("fpdf2 not installed")

        pdf = ForestGuardReportPDF(report_type=ReportType.JUDICIAL)
        pdf.report_id = report_id
        pdf.alias_nb_pages()
        pdf.add_page()

        pdf.set_font("Arial", "B", 18)
        pdf.set_text_color(*COLORS["SECONDARY"])
        pdf.cell(0, 10, "REPORTE JUDICIAL FORENSE", 0, 1, "C")
        pdf.ln(4)

        pdf.set_font("Courier", "B", 12)
        pdf.set_text_color(*COLORS["ACCENT"])
        pdf.cell(0, 8, f"REF: {report_id}", 0, 1, "C")
        pdf.ln(6)

        pdf.set_fill_color(*COLORS["BG_LIGHT"])
        pdf.rect(10, pdf.get_y(), 190, 45, "F")
        pdf.set_y(pdf.get_y() + 4)
        pdf.set_font("Arial", "B", 10)
        pdf.set_text_color(*COLORS["TEXT"])

        info_items = [
            ("Evento:", fire.id),
            ("Provincia:", fire.province or "No especificada"),
            ("Departamento:", fire.department or "No especificado"),
            ("Inicio:", fire.start_date.strftime("%d/%m/%Y %H:%M")),
            ("Fin:", fire.end_date.strftime("%d/%m/%Y %H:%M")),
            ("Detecciones:", str(fire.total_detections)),
            (
                "Área estimada (ha):",
                f"{fire.estimated_area_hectares:.2f}"
                if fire.estimated_area_hectares
                else "N/D",
            ),
        ]

        for label, value in info_items:
            pdf.set_x(15)
            pdf.cell(45, 6, label, 0, 0)
            pdf.set_font("Arial", "", 10)
            pdf.cell(0, 6, value, 0, 1)
            pdf.set_font("Arial", "B", 10)

        pdf.ln(8)

        pdf.set_font("Arial", "B", 12)
        pdf.set_text_color(*COLORS["SECONDARY"])
        pdf.cell(0, 8, "Cronología del evento", 0, 1, "L")
        pdf.set_font("Arial", "", 10)
        pdf.set_text_color(*COLORS["TEXT"])

        if detections:
            first = detections[0].detected_at
            last = detections[-1].detected_at
            pdf.cell(
                0, 6, f"Primera detección: {first.strftime('%d/%m/%Y %H:%M')}", 0, 1
            )
            pdf.cell(0, 6, f"Última detección: {last.strftime('%d/%m/%Y %H:%M')}", 0, 1)
            pdf.cell(0, 6, f"Total registros: {len(detections)}", 0, 1)
            pdf.ln(2)

            for idx, det in enumerate(detections[:12], start=1):
                frp = (
                    f"FRP {det.fire_radiative_power:.1f}"
                    if det.fire_radiative_power is not None
                    else "FRP N/D"
                )
                pdf.cell(
                    0,
                    5,
                    f"{idx:02d}. {det.detected_at.strftime('%d/%m/%Y %H:%M')} - {frp}",
                    0,
                    1,
                )
            if len(detections) > 12:
                pdf.cell(
                    0, 5, f"... {len(detections) - 12} registros adicionales", 0, 1
                )
        else:
            pdf.cell(0, 6, "Sin registros de detecciones asociadas.", 0, 1)

        pdf.ln(6)
        self._add_propagation_map(pdf, detections, fire)

        pdf.ln(6)
        pdf.set_font("Arial", "B", 12)
        pdf.set_text_color(*COLORS["SECONDARY"])
        pdf.cell(0, 8, "Condiciones climáticas", 0, 1, "L")
        pdf.set_font("Arial", "", 10)
        pdf.set_text_color(*COLORS["TEXT"])

        if request.include_climate and climate:
            pdf.cell(
                0,
                6,
                f"Fecha referencia: {climate.reference_date.strftime('%d/%m/%Y')}",
                0,
                1,
            )
            pdf.cell(
                0, 6, f"Temp. media: {climate.temp_mean_celsius or 'N/D'} °C", 0, 1
            )
            pdf.cell(
                0,
                6,
                f"Temp. máx/mín: {climate.temp_max_celsius or 'N/D'} / {climate.temp_min_celsius or 'N/D'} °C",
                0,
                1,
            )
            pdf.cell(0, 6, f"Viento: {climate.wind_speed_kmh or 'N/D'} km/h", 0, 1)
            pdf.cell(
                0,
                6,
                f"Humedad relativa: {climate.relative_humidity_pct or 'N/D'} %",
                0,
                1,
            )
            pdf.cell(
                0, 6, f"Precipitación: {climate.precipitation_mm or 'N/D'} mm", 0, 1
            )
            pdf.cell(0, 6, f"KBDI: {climate.kbdi or 'N/D'}", 0, 1)
            pdf.cell(0, 6, f"Fuente: {climate.data_source or 'ERA5-Land'}", 0, 1)
        else:
            pdf.multi_cell(
                0,
                5,
                "No se encontraron datos climáticos asociados. "
                "El reporte se emite con esta salvedad.",
                0,
                "J",
            )

        if request.include_imagery:
            if images:
                pdf.add_page()
                pdf.set_font("Arial", "B", 12)
                pdf.set_text_color(*COLORS["SECONDARY"])
                pdf.cell(0, 8, "Evidencia satelital", 0, 1, "L")
                pdf.ln(4)
                for idx, img in enumerate(images):
                    if idx > 0 and idx % 2 == 0:
                        pdf.add_page()
                    self._add_image_to_pdf(pdf, img, width=180)
                    pdf.ln(6)
            else:
                pdf.ln(4)
                pdf.set_font("Arial", "I", 9)
                pdf.cell(
                    0,
                    6,
                    "No se encontraron imágenes reproducibles para el evento.",
                    0,
                    1,
                )

        pdf.add_page()
        pdf.set_font("Arial", "B", 12)
        pdf.set_text_color(*COLORS["SECONDARY"])
        pdf.cell(0, 8, "Cadena de custodia digital", 0, 1, "L")
        pdf.set_font("Arial", "", 10)
        pdf.set_text_color(*COLORS["TEXT"])

        pdf.cell(0, 6, f"Generado: {generated_at.strftime('%d/%m/%Y %H:%M')}", 0, 1)
        if request.requester_name:
            pdf.cell(0, 6, f"Solicitante: {request.requester_name}", 0, 1)
        if request.case_reference:
            pdf.cell(0, 6, f"Referencia: {request.case_reference}", 0, 1)
        if request.requester_id:
            pdf.cell(0, 6, f"ID solicitante: {request.requester_id}", 0, 1)

        pdf.ln(2)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 6, "Imágenes utilizadas:", 0, 1)
        pdf.set_font("Arial", "", 9)

        if images:
            for img in images:
                vis_params = img.visualization_params or {}
                bands = vis_params.get("bands")
                bands_text = f" bandas={bands}" if bands else ""
                date_text = img.acquisition_date.strftime("%d/%m/%Y")
                time_text = ""
                if img.acquisition_time:
                    if hasattr(img.acquisition_time, "strftime"):
                        time_text = f" {img.acquisition_time.strftime('%H:%M')}"
                    else:
                        time_text = f" {img.acquisition_time}"
                pdf.multi_cell(
                    0,
                    4,
                    f"- {img.gee_system_index or img.image_id} | {date_text}{time_text} | "
                    f"{img.vis_type}{bands_text} | Nubes {img.cloud_cover:.0f}%",
                    0,
                    "L",
                )
        else:
            pdf.cell(0, 5, "Sin imágenes disponibles.", 0, 1)

        pdf.ln(4)
        pdf.set_font("Arial", "I", 8)
        pdf.multi_cell(
            0,
            4,
            "El hash SHA-256 del PDF se almacena en la base de datos para verificación. "
            "Este reporte fue generado automáticamente por ForestGuard para uso pericial.",
            0,
            "J",
        )

        pdf.add_page()
        verification_url = f"https://forestguard.freedynamicdns.org/verify/{report_id}"
        add_verification_block(
            pdf,
            verification_url=verification_url,
            title="Verificacion y Autenticidad",
            note="El hash SHA-256 del PDF se almacena en la base de datos para verificacion.",
        )

        return bytes(pdf.output())

    def _add_propagation_map(
        self,
        pdf: FPDF,
        detections: List[DetectionSnapshot],
        fire: FireEventSnapshot,
    ) -> None:
        pdf.set_font("Arial", "B", 12)
        pdf.set_text_color(*COLORS["SECONDARY"])
        pdf.cell(0, 6, "Mapa de propagación", 0, 1, "L")
        pdf.set_font("Arial", "", 9)
        pdf.set_text_color(*COLORS["TEXT"])

        map_x = 15
        map_y = pdf.get_y() + 2
        map_w = 180
        map_h = 60
        pdf.rect(map_x, map_y, map_w, map_h)

        points = [
            (d.longitude, d.latitude)
            for d in detections
            if d.longitude is not None and d.latitude is not None
        ]
        if (
            not points
            and fire.centroid_lon is not None
            and fire.centroid_lat is not None
        ):
            points = [(fire.centroid_lon, fire.centroid_lat)]

        if points:
            min_lon = min(p[0] for p in points)
            max_lon = max(p[0] for p in points)
            min_lat = min(p[1] for p in points)
            max_lat = max(p[1] for p in points)

            if min_lon == max_lon:
                min_lon -= 0.01
                max_lon += 0.01
            if min_lat == max_lat:
                min_lat -= 0.01
                max_lat += 0.01

            step = max(1, int(len(points) / 150))
            for idx, (lon, lat) in enumerate(points[::step]):
                x = map_x + ((lon - min_lon) / (max_lon - min_lon)) * map_w
                y = map_y + map_h - ((lat - min_lat) / (max_lat - min_lat)) * map_h
                pdf.set_fill_color(*COLORS["ACCENT"])
                pdf.ellipse(x - 1, y - 1, 2, 2, style="F")

        pdf.set_y(map_y + map_h + 4)

    def _record_report_audit(
        self,
        report_id: str,
        request: ReportRequest,
        verification_hash: str,
        pdf_url: Optional[str],
        images: List[ImageEvidence],
        generated_at: datetime,
        report_type: str,
        resource_type: str,
        resource_id: str,
        extra_details: Optional[Dict[str, Any]] = None,
    ) -> None:
        if self._db is None:
            return
        details = {
            "report_id": report_id,
            "report_type": report_type,
            "verification_hash": verification_hash,
            "pdf_url": pdf_url,
            "generated_at": generated_at.isoformat(),
            "requester_name": request.requester_name,
            "requester_id": request.requester_id,
            "case_reference": request.case_reference,
            "images_count": len(images),
            "image_cost_usd": self._resolve_report_image_cost(),
            "language": request.language,
        }
        if extra_details:
            details.update(extra_details)
        try:
            self._db.execute(
                text(
                    """
                    INSERT INTO audit_events (
                        principal_id,
                        principal_role,
                        action,
                        resource_type,
                        resource_id,
                        details
                    ) VALUES (
                        :principal_id,
                        :principal_role,
                        :action,
                        :resource_type,
                        :resource_id,
                        :details
                    )
                    """
                ),
                {
                    "principal_id": request.requester_id,
                    "principal_role": "api_key"
                    if request.requester_id
                    else "anonymous",
                    "action": "report_generated",
                    "resource_type": resource_type,
                    "resource_id": resource_id,
                    "details": json.dumps(details),
                },
            )
            self._db.commit()
        except SQLAlchemyError as exc:
            logger.warning(
                "Failed to write audit_event for report %s: %s", report_id, exc
            )
            self._db.rollback()

    # =========================================================================
    # UC-09: PAQUETES DE EVIDENCIA
    # =========================================================================

    def _generate_evidence_package(
        self, request: ReportRequest, report_id: str
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
                "verified_at": datetime.now().isoformat(),
            }

        except Exception as e:
            return {"report_id": report_id, "is_valid": False, "error": str(e)}

    # =========================================================================
    # HEALTH CHECK
    # =========================================================================

    def health_check(self) -> Dict[str, Any]:
        """Verifica estado del servicio."""

        gee_status = self._gee.health_check()
        storage_status = self._storage.health_check()

        all_healthy = (
            gee_status.get("status") == "healthy"
            and storage_status.get("status") == "healthy"
        )

        return {
            "service": "ERS",
            "status": "healthy" if all_healthy else "degraded",
            "pdf_generation": FPDF_AVAILABLE,
            "gee_status": gee_status.get("status"),
            "storage_status": storage_status.get("status"),
            "supported_report_types": [rt.value for rt in ReportType],
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
            bbox={"west": -60.5, "south": -27.0, "east": -60.3, "north": -26.8},
            max_images=5,
            vis_types=["RGB", "NDVI"],
            include_pre_fire=True,
            post_fire_frequency="annual",
        )

        print(f"\nGenerating report...")
        result = ers.generate_report(request)

        print(f"\nReport Result:")
        print(f"  ID: {result.report_id}")
        print(f"  Status: {result.status.value}")
        print(f"  PDF URL: {result.pdf_url}")
        print(f"  Images: {len(result.images)}")
        print(f"  Hash: {result.verification_hash}")
