"""Tests for all PII sanitization patterns (BL-008)."""
from app.core.sanitizer import redact_pii


class TestRedactPii:
    def test_email_redacted(self):
        assert "user@example.com" not in redact_pii("Contact user@example.com for info")
        assert "***@example.com" in redact_pii("Contact user@example.com for info")

    def test_ipv4_redacted(self):
        result = redact_pii("Client IP: 192.168.1.100")
        assert "192.168.1.100" not in result
        assert "192.168.1.***" in result

    def test_jwt_redacted(self):
        token = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.abc123def456"
        result = redact_pii(f"Token: {token}")
        assert token not in result
        assert "[JWT_REDACTED]" in result

    def test_api_key_redacted(self):
        key = "a" * 32
        result = redact_pii(f"Key: {key}")
        assert key not in result
        assert "[API_KEY_REDACTED]" in result

    def test_password_redacted(self):
        result = redact_pii("password=supersecret123")
        assert "supersecret123" not in result
        assert "[REDACTED]" in result

    def test_phone_ar_redacted(self):
        result = redact_pii("Llamar a +54 11 4567-8901 urgente")
        assert "4567" not in result
        assert "[PHONE_REDACTED]" in result

    def test_phone_ar_no_spaces(self):
        result = redact_pii("Tel: +541145678901")
        assert "45678901" not in result
        assert "[PHONE_REDACTED]" in result

    def test_phone_ar_with_dashes(self):
        result = redact_pii("Tel: 54-11-45678901")
        assert "45678901" not in result
        assert "[PHONE_REDACTED]" in result

    def test_cuit_redacted(self):
        result = redact_pii("CUIT del usuario: 20-12345678-9")
        assert "20-12345678-9" not in result
        assert "[CUIT_REDACTED]" in result

    def test_cuil_redacted(self):
        result = redact_pii("CUIL: 27-3456789-0")
        assert "27-3456789-0" not in result
        assert "[CUIT_REDACTED]" in result

    def test_non_string_handled(self):
        assert redact_pii(12345) == "12345"
        assert redact_pii(None) == "None"

    def test_clean_message_unchanged(self):
        msg = "Fire event detected in Cordoba province"
        assert redact_pii(msg) == msg
