"""
Servicio de generación de PDF para ForestGuard.

Genera PDFs profesionales usando fpdf2 con layout automático.
Reutilizable por: task PDF post-HD, endpoint judicial, closure reports.

No escribe archivos temporales: genera en BytesIO y retorna bytes.
"""

import hashlib
import io
import logging
import os
from datetime import datetime, timezone
from typing import List, Optional

from fpdf import FPDF

logger = logging.getLogger(__name__)


class _ForestGuardPDF(FPDF):
    """Custom FPDF class with ForestGuard header/footer."""

    def __init__(self, title: str = ""):
        super().__init__()
        self._doc_title = title

    def header(self):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(100, 100, 100)
        self.cell(0, 8, "ForestGuard", new_x="LMARGIN", new_y="NEXT", align="R")
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Página {self.page_no()}/{{nb}}", align="C")


class PdfGenerationService:
    """Generates PDFs from HD exploration results."""

    def generate_exploration_pdf(
        self,
        investigation_id: str,
        job_id: str,
        hd_results: dict,
        investigation_title: Optional[str] = None,
        max_images: int = 6,
        image_dpi: int = 150,
    ) -> tuple[bytes, str]:
        """
        Generate exploration PDF in memory.

        Args:
            investigation_id: UUID of the investigation.
            job_id: UUID of the HD job.
            hd_results: dict with HD job results.
            investigation_title: optional investigation title.
            max_images: max images to embed (from system_parameters).
            image_dpi: image resolution for embedded images.

        Returns:
            tuple of (pdf_bytes, sha256_hash)
        """
        title = investigation_title or "Reporte de exploración satelital"
        now = datetime.now(timezone.utc)

        pdf = _ForestGuardPDF(title=title)
        pdf.alias_nb_pages()
        pdf.set_auto_page_break(auto=True, margin=20)
        pdf.add_page()

        # Title
        pdf.set_font("Helvetica", "B", 18)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 12, title, new_x="LMARGIN", new_y="NEXT", align="L")
        pdf.ln(4)

        # Metadata
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(120, 120, 120)
        pdf.cell(
            0,
            5,
            f"Generado por ForestGuard — {now.strftime('%d/%m/%Y %H:%M')} UTC",
            new_x="LMARGIN",
            new_y="NEXT",
        )
        pdf.cell(
            0,
            5,
            f"ID investigación: {investigation_id}",
            new_x="LMARGIN",
            new_y="NEXT",
        )
        pdf.cell(
            0,
            5,
            f"ID job: {job_id}",
            new_x="LMARGIN",
            new_y="NEXT",
        )
        pdf.ln(8)

        # Summary
        images_list: List[dict] = hd_results.get("images", [])
        total_images = len(images_list)
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(
            0,
            7,
            f"Resumen: {total_images} imagen(es) HD generada(s)",
            new_x="LMARGIN",
            new_y="NEXT",
        )
        pdf.ln(6)

        # Image metadata table
        if images_list:
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_fill_color(46, 117, 182)
            pdf.set_text_color(255, 255, 255)
            col_widths = [15, 40, 40, 35, 40]
            headers = ["#", "Banda", "Fecha", "Estado", "Sensor"]
            for i, header in enumerate(headers):
                pdf.cell(col_widths[i], 7, header, border=1, fill=True, align="C")
            pdf.ln()

            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(0, 0, 0)
            for idx, img_info in enumerate(images_list[:max_images]):
                if idx % 2 == 1:
                    pdf.set_fill_color(245, 245, 245)
                    fill = True
                else:
                    fill = False
                row_data = [
                    str(idx + 1),
                    str(img_info.get("band", "N/A")),
                    str(img_info.get("target_date", "N/A")),
                    str(img_info.get("status", "N/A")),
                    str(img_info.get("sensor", "N/A")),
                ]
                for i, cell_text in enumerate(row_data):
                    pdf.cell(
                        col_widths[i], 6, cell_text, border=1, fill=fill, align="C"
                    )
                pdf.ln()
            pdf.ln(8)

        # Embed images (if local paths available)
        embedded_count = 0
        for img_info in images_list[:max_images]:
            local_path = img_info.get("local_path")
            if local_path and embedded_count < max_images and os.path.exists(local_path):
                try:
                    pdf.set_font("Helvetica", "B", 10)
                    pdf.cell(
                        0,
                        7,
                        f"Imagen {embedded_count + 1}: "
                        f"{img_info.get('band', 'N/A')} — "
                        f"{img_info.get('target_date', '')}",
                        new_x="LMARGIN",
                        new_y="NEXT",
                    )
                    pdf.ln(3)
                    pdf.image(local_path, w=140)
                    pdf.ln(8)
                    embedded_count += 1
                except Exception as e:
                    logger.warning("Could not embed image %s: %s", local_path, e)

        # Verification footer
        pdf.ln(15)
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(150, 150, 150)
        pdf.multi_cell(
            0,
            4,
            "Este documento fue generado automáticamente por ForestGuard. "
            "Las imágenes provienen de Google Earth Engine y son de dominio público. "
            "El hash SHA-256 de este documento puede verificarse para comprobar su integridad.",
        )

        # Build PDF
        pdf_bytes = pdf.output()
        if isinstance(pdf_bytes, str):
            pdf_bytes = pdf_bytes.encode("latin-1")

        sha256 = hashlib.sha256(pdf_bytes).hexdigest()
        logger.info(
            "PDF generated: %d bytes, SHA-256: %s..., %d images embedded",
            len(pdf_bytes),
            sha256[:12],
            embedded_count,
        )

        return pdf_bytes, sha256
