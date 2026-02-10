"""
Módulo de Generación de Certificados PDF para ForestGuard.

Este módulo se encarga de diseñar y compilar los certificados de registro
de incendios en formato PDF, cumpliendo con los estándares de identidad visual
de la organización. Utiliza la librería `fpdf2`.

Autor: ForestGuard Dev Team
Versión: 2.1.0 (Bug fix + QR)
"""

import io
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import qrcode
from fpdf import FPDF

# --- Configuración de Estilos y Constantes ---

# Colores Corporativos (RGB)
COLORS = {
    "PRIMARY": (46, 125, 50),  # Verde Forestal
    "SECONDARY": (27, 94, 32),  # Verde Oscuro
    "ACCENT": (200, 0, 0),  # Rojo Alerta
    "TEXT": (50, 50, 50),  # Gris Oscuro
    "BG_LIGHT": (245, 245, 245),  # Gris Muy Claro
    "WHITE": (255, 255, 255),
    "GRAY_LIGHT": (230, 230, 230),
    "GRAY_TEXT": (128, 128, 128),
}

# Rutas de Recursos
BASE_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = BASE_DIR / "assets"
LOGO_PATH = ASSETS_DIR / "logo-horizontal.png"


class ForestGuardPDF(FPDF):
    """
    Clase personalizada para PDFs de ForestGuard.
    Extiende FPDF para implementar encabezados y pies de página corporativos.
    """

    def header(self) -> None:
        """Genera el encabezado corporativo con logo y título."""
        self.set_fill_color(*COLORS["PRIMARY"])
        self.rect(0, 0, 210, 35, "F")

        offset_x = 10
        if LOGO_PATH.exists():
            try:
                self.image(str(LOGO_PATH), 10, 5, 25)
                offset_x = 40
            except Exception:
                pass

        self.set_font("Arial", "B", 20)
        self.set_text_color(*COLORS["WHITE"])
        self.set_xy(offset_x, 10)
        self.cell(0, 10, "ForestGuard", 0, 1, "L")

        self.set_font("Arial", "", 10)
        self.set_xy(offset_x, 18)
        self.cell(0, 10, "Sistema Nacional de Monitoreo y Recuperacion", 0, 1, "L")
        self.ln(15)

    def footer(self) -> None:
        """Genera el pie de página corporativo con logo pequeño y paginación."""
        self.set_y(-20)
        self.set_draw_color(*COLORS["PRIMARY"])
        self.line(10, 277, 200, 277)

        # Logo pequeño en el footer (izquierda)
        if LOGO_PATH.exists():
            try:
                self.image(str(LOGO_PATH), x=10, y=279, w=12)
            except Exception:
                pass

        self.set_font("Arial", "I", 8)
        self.set_text_color(*COLORS["GRAY_TEXT"])
        self.set_x(25)
        self.cell(
            0, 5, "Documento generado automaticamente por ForestGuard.", 0, 1, "C"
        )

        page_str = f"Pagina {self.page_no()}/{{nb}}"
        self.set_x(25)
        self.cell(0, 5, page_str, 0, 0, "C")


def generate_certificate_pdf(
    certificate: Any, event_data: Dict[str, Any], verification_url: str
) -> bytes:
    """
    Genera el archivo PDF del certificado de quema con código QR.

    Args:
        certificate: Objeto con datos del certificado (certificate_number, issued_to, etc).
        event_data: Dict con datos del evento (date, province, lat, lon, hectares, frp).
        verification_url: URL pública para validar el certificado vía QR.

    Returns:
        bytes: Contenido del PDF.
    """

    # Inicialización del PDF
    pdf = ForestGuardPDF()
    pdf.alias_nb_pages()
    pdf.add_page()

    # --- TÍTULO ---
    pdf.set_y(45)
    pdf.set_font("Arial", "B", 18)
    pdf.set_text_color(*COLORS["SECONDARY"])
    pdf.cell(0, 10, "CERTIFICADO DE REGISTRO DE QUEMA", 0, 1, "C")

    pdf.set_font("Courier", "B", 12)
    pdf.set_text_color(*COLORS["ACCENT"])
    pdf.cell(0, 10, f"REF: {certificate.certificate_number}", 0, 1, "C")
    pdf.ln(5)

    # --- CAJA DE INFORMACIÓN + QR ---
    pdf.set_fill_color(*COLORS["BG_LIGHT"])
    pdf.set_draw_color(200, 200, 200)

    # Caja izquierda (Texto) - Ancho reducido para dar espacio al QR
    pdf.rect(10, 75, 140, 45, "FD")

    pdf.set_y(80)

    def print_info_row(label: str, value: str):
        pdf.set_x(15)
        pdf.set_font("Arial", "B", 11)
        pdf.set_text_color(*COLORS["TEXT"])
        pdf.cell(35, 8, label, 0, 0)
        pdf.set_font("Arial", "", 11)
        pdf.cell(0, 8, value, 0, 1)

    print_info_row("SOLICITANTE:", str(certificate.issued_to))
    print_info_row("EMAIL:", str(certificate.requester_email))

    date_str = (
        certificate.issued_at.strftime("%d/%m/%Y %H:%M")
        if hasattr(certificate.issued_at, "strftime")
        else str(certificate.issued_at)
    )
    print_info_row("EMISION:", date_str)

    # --- GENERACIÓN E INSERCIÓN DEL QR ---
    # Normalizar URL para que sea escaneable (debe incluir esquema http/https)
    verification_url_str = str(verification_url).strip()
    if verification_url_str and not verification_url_str.startswith(
        ("http://", "https://")
    ):
        verification_url_str = "https://" + verification_url_str.lstrip("/")

    # Generar QR robusto (mejor legibilidad/escaneo)
    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_Q,
        box_size=6,
        border=4,
    )
    qr.add_data(verification_url_str)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")

    # Convertir imagen PIL a bytes para FPDF2
    qr_buffer = io.BytesIO()
    qr_img.save(qr_buffer, format="PNG")
    qr_buffer.seek(0)

    # Insertar QR
    pdf.image(qr_buffer, x=155, y=75, w=45)

    pdf.set_xy(155, 121)
    pdf.set_font("Arial", "B", 8)
    pdf.set_text_color(*COLORS["TEXT"])
    pdf.cell(45, 5, "ESCANEAR PARA VALIDAR", 0, 1, "C")

    pdf.set_xy(155, 126)
    pdf.set_font("Arial", "", 6)
    pdf.set_text_color(*COLORS["GRAY_TEXT"])
    pdf.multi_cell(45, 3, verification_url_str, 0, "C")

    # --- DETALLES DEL EVENTO ---
    pdf.set_y(135)
    pdf.set_font("Arial", "B", 14)
    pdf.set_text_color(*COLORS["SECONDARY"])
    pdf.cell(0, 10, "Detalles del Evento Satelital", 0, 1, "L")

    pdf.set_draw_color(*COLORS["SECONDARY"])
    pdf.line(10, 145, 100, 145)

    pdf.ln(5)
    pdf.set_font("Arial", "", 12)
    pdf.set_text_color(*COLORS["TEXT"])

    items = [
        f"Fecha de Deteccion: {event_data.get('date', 'N/A')}",
        f"Provincia: {event_data.get('province', 'N/A')}",
        f"Coordenadas: Lat {event_data.get('lat', 0):.5f}, Lon {event_data.get('lon', 0):.5f}",
        f"Superficie Estimada: {event_data.get('hectares', 0):.2f} hectareas",
        f"Intensidad (FRP): {event_data.get('frp', 0):.2f} MW",
    ]

    for item in items:
        pdf.set_x(15)
        pdf.cell(5, 8, chr(149), 0, 0)
        pdf.cell(0, 8, item, 0, 1)

    # --- DISCLAIMER ---
    pdf.set_y(210)
    pdf.set_font("Arial", "I", 10)
    pdf.set_text_color(*COLORS["TEXT"])
    legal_text = (
        "Este certificado acredita la existencia de registros satelitales en la base de datos "
        "de ForestGuard. No reemplaza peritajes en terreno realizados por autoridades "
        "competentes, pero sirve como prueba de registro digital inmutable."
    )
    pdf.multi_cell(0, 6, legal_text)

    # --- FIRMA DIGITAL (HASH) ---
    pdf.set_y(240)
    pdf.set_fill_color(*COLORS["GRAY_LIGHT"])
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Courier", "", 9)

    hash_block = f"FIRMA DIGITAL (SHA-256):\n{certificate.data_hash}"
    pdf.multi_cell(0, 5, hash_block, 1, "C", True)

    # FIX CRÍTICO: Generar el PDF correctamente
    return bytes(pdf.output())
