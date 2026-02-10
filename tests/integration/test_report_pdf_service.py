import pytest

import app.services.report_pdf_service as report_pdf_service


@pytest.mark.skipif(
    not report_pdf_service.FPDF_AVAILABLE,
    reason="fpdf2 or qrcode not installed",
)
def test_report_pdf_service_integration():
    from fpdf import FPDF

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 10, "Test report content", 0, 1)

    report_pdf_service.add_verification_block(
        pdf,
        verification_url="example.com/verify/RPT-TEST",
        title="Verificacion y Autenticidad",
    )

    pdf_bytes = bytes(pdf.output())
    assert len(pdf_bytes) > 500


def test_report_pdf_service_regression_url_normalization():
    url = report_pdf_service.normalize_verification_url("example.com/verify/RPT-TEST")
    assert url.startswith("https://")


@pytest.mark.skipif(
    not report_pdf_service.FPDF_AVAILABLE,
    reason="fpdf2 or qrcode not installed",
)
def test_report_pdf_service_smoke():
    png_bytes = report_pdf_service.build_qr_image_bytes(
        "https://example.com/verify/RPT-TEST"
    )
    assert png_bytes.startswith(b"\x89PNG\r\n\x1a\n")
