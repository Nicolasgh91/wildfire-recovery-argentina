"""
Utilities for generating report PDFs with QR and verification hints.

This module centralizes QR generation and verification blocks used by
judicial and historical reports (T4.3).
"""

from __future__ import annotations

from io import BytesIO
from typing import Optional

try:
    import qrcode
    from fpdf import FPDF

    FPDF_AVAILABLE = True
except Exception:  # pragma: no cover - optional dependency
    FPDF_AVAILABLE = False
    FPDF = object  # type: ignore
    qrcode = None  # type: ignore


def normalize_verification_url(url: str) -> str:
    """Ensure verification URL includes scheme for QR readability."""
    url = str(url).strip()
    if not url:
        return ""
    if url.startswith(("http://", "https://")):
        return url
    return "https://" + url.lstrip("/")


def build_qr_image_bytes(url: str, box_size: int = 6, border: int = 4) -> bytes:
    """Build a QR PNG image for a verification URL."""
    if not FPDF_AVAILABLE or qrcode is None:
        raise RuntimeError("fpdf2 or qrcode not installed")

    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_Q,
        box_size=box_size,
        border=border,
    )
    qr.add_data(normalize_verification_url(url))
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")

    buffer = BytesIO()
    qr_img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer.read()


def add_verification_block(
    pdf: FPDF,
    verification_url: str,
    title: str = "Verificacion y Autenticidad",
    note: Optional[str] = None,
    qr_size: int = 50,
) -> None:
    """
    Insert a verification block with QR code into the current PDF page.
    The caller controls page breaks.
    """
    if not FPDF_AVAILABLE:
        raise RuntimeError("fpdf2 not installed")

    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, title, 0, 1, "L")
    pdf.ln(4)

    qr_bytes = build_qr_image_bytes(verification_url)
    qr_buffer = BytesIO(qr_bytes)
    pdf.image(qr_buffer, x=80, y=pdf.get_y(), w=qr_size)
    pdf.set_y(pdf.get_y() + qr_size + 4)
    pdf.set_font("Arial", "B", 9)
    pdf.cell(0, 6, "Escanear para verificar autenticidad", 0, 1, "C")
    pdf.set_font("Arial", "", 8)
    pdf.multi_cell(0, 4, normalize_verification_url(verification_url), 0, "C")

    if note:
        pdf.ln(4)
        pdf.set_font("Arial", "I", 8)
        pdf.multi_cell(0, 4, note, 0, "J")
