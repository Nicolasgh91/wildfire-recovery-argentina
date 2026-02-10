import pytest
from unittest.mock import MagicMock

from app.core.config import settings
from app.core.rate_limiter import reset_rate_limiter_state


@pytest.fixture(autouse=True)
def _smtp_settings(monkeypatch):
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.test", raising=False)
    monkeypatch.setattr(settings, "SMTP_PORT", 587, raising=False)
    monkeypatch.setattr(settings, "SMTP_USER", "user@test", raising=False)
    monkeypatch.setattr(settings, "SMTP_PASSWORD", "pass", raising=False)
    reset_rate_limiter_state()


def test_contact_valid_no_attachment(client, monkeypatch):
    mock_task = MagicMock()
    monkeypatch.setattr("app.api.v1.contact.send_contact_email_task.delay", mock_task)

    response = client.post(
        "/api/v1/contact",
        data={
            "name": "Juan Perez",
            "email": "juan@example.com",
            "subject": "Consulta",
            "message": "Necesito informacion sobre incendios recientes.",
        },
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["status"] == "accepted"
    assert payload["request_id"]
    
    # Verify task was called
    mock_task.assert_called_once()


def test_contact_invalid_attachment_type(client, monkeypatch):
    mock_task = MagicMock()
    monkeypatch.setattr("app.api.v1.contact.send_contact_email_task.delay", mock_task)

    response = client.post(
        "/api/v1/contact",
        data={
            "name": "Juan Perez",
            "email": "juan@example.com",
            "subject": "Consulta",
            "message": "Adjunto un archivo.",
        },
        files={
            "attachment": ("malware.exe", b"malware", "application/octet-stream"),
        },
    )

    assert response.status_code == 422
    mock_task.assert_not_called()


def test_contact_attachment_too_large(client, monkeypatch):
    mock_task = MagicMock()
    monkeypatch.setattr("app.api.v1.contact.send_contact_email_task.delay", mock_task)

    big_payload = b"a" * (5 * 1024 * 1024 + 1)
    response = client.post(
        "/api/v1/contact",
        data={
            "name": "Juan Perez",
            "email": "juan@example.com",
            "subject": "Consulta",
            "message": "Adjunto un archivo grande.",
        },
        files={
            "attachment": ("big.pdf", big_payload, "application/pdf"),
        },
    )

    assert response.status_code == 413
    mock_task.assert_not_called()


def test_contact_rate_limit_returns_429_after_10_requests(client, monkeypatch):
    mock_task = MagicMock()
    monkeypatch.setattr("app.api.v1.contact.send_contact_email_task.delay", mock_task)

    payload = {
        "name": "Juan Perez",
        "email": "juan@example.com",
        "subject": "Consulta",
        "message": "Mensaje de prueba para validar limite por minuto.",
    }
    headers = {"X-Forwarded-For": "203.0.113.10"}

    for _ in range(10):
        response = client.post("/api/v1/contact", data=payload, headers=headers)
        assert response.status_code == 202
        
    assert mock_task.call_count == 10

    blocked_response = client.post("/api/v1/contact", data=payload, headers=headers)
    assert blocked_response.status_code == 429
    assert mock_task.call_count == 10
