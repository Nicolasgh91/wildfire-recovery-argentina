import pytest

import app.services.report_pdf_service as report_pdf_service


def test_normalize_verification_url_adds_scheme():
    url = report_pdf_service.normalize_verification_url("example.com/verify/123")
    assert url.startswith("https://")


@pytest.mark.skipif(
    not report_pdf_service.FPDF_AVAILABLE,
    reason="fpdf2 or qrcode not installed",
)
def test_build_qr_image_bytes_png_signature():
    png_bytes = report_pdf_service.build_qr_image_bytes(
        "https://example.com/verify/123"
    )
    assert png_bytes.startswith(b"\x89PNG\r\n\x1a\n")
