import hashlib
import pytest
from unittest.mock import MagicMock

from app.core.config import settings
from app.core.rate_limiter import reset_rate_limiter_state
from app.services.contact_service import ContactService


@pytest.fixture(autouse=True)
def _smtp_settings(monkeypatch):
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.test", raising=False)
    monkeypatch.setattr(settings, "SMTP_PORT", 587, raising=False)
    monkeypatch.setattr(settings, "SMTP_USER", "user@test", raising=False)
    monkeypatch.setattr(settings, "SMTP_PASSWORD", "pass", raising=False)
    reset_rate_limiter_state()


def test_contact_valid_no_attachment(client, monkeypatch, caplog):
    mock_task = MagicMock()
    fallback_calls = []

    async def _mock_send_contact_email(self, message):
        fallback_calls.append(message)

    monkeypatch.setattr("app.api.v1.contact.send_contact_email_task.delay", mock_task)
    monkeypatch.setattr(ContactService, "send_contact_email", _mock_send_contact_email)
    caplog.set_level("INFO", logger="app.api.v1.contact")

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
    assert "juan@example.com" not in caplog.text
    mock_task.assert_called_once()
    assert fallback_calls == []


def test_contact_fallback_to_sync_smtp_when_enqueue_fails(client, monkeypatch):
    smtp_calls = []

    def _raise_enqueue_error(*args, **kwargs):
        raise RuntimeError("redis unavailable")

    async def _mock_send_contact_email(self, message):
        smtp_calls.append(message)

    monkeypatch.setattr(
        "app.api.v1.contact.send_contact_email_task.delay",
        _raise_enqueue_error,
    )
    monkeypatch.setattr(ContactService, "send_contact_email", _mock_send_contact_email)

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
    assert len(smtp_calls) == 1


def test_contact_returns_503_when_enqueue_and_smtp_fallback_fail(client, monkeypatch):
    def _raise_enqueue_error(*args, **kwargs):
        raise RuntimeError("redis unavailable")

    async def _raise_smtp_error(self, message):
        raise RuntimeError("smtp unavailable")

    monkeypatch.setattr(
        "app.api.v1.contact.send_contact_email_task.delay",
        _raise_enqueue_error,
    )
    monkeypatch.setattr(ContactService, "send_contact_email", _raise_smtp_error)

    response = client.post(
        "/api/v1/contact",
        data={
            "name": "Juan Perez",
            "email": "juan@example.com",
            "subject": "Consulta",
            "message": "Necesito informacion sobre incendios recientes.",
        },
    )

    assert response.status_code == 503
    assert (
        response.json()["detail"]
        == "Service temporarily unavailable. Please try again later."
    )


def test_contact_fallback_preserves_attachment_metadata(client, monkeypatch):
    attachment_content = b"hello-fallback"
    expected_sha = hashlib.sha256(attachment_content).hexdigest()
    sent_messages = []

    def _raise_enqueue_error(*args, **kwargs):
        raise RuntimeError("redis unavailable")

    async def _mock_send_contact_email(self, message):
        sent_messages.append(message)

    monkeypatch.setattr(
        "app.api.v1.contact.send_contact_email_task.delay",
        _raise_enqueue_error,
    )
    monkeypatch.setattr(ContactService, "send_contact_email", _mock_send_contact_email)

    response = client.post(
        "/api/v1/contact",
        data={
            "name": "Juan Perez",
            "email": "juan@example.com",
            "subject": "Consulta",
            "message": "Adjunto un archivo.",
        },
        files={
            "attachment": ("note.pdf", attachment_content, "application/pdf"),
        },
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["status"] == "accepted"
    assert payload["attachment"]["filename"] == "note.pdf"
    assert payload["attachment"]["size_bytes"] == len(attachment_content)
    assert payload["attachment"]["sha256"] == expected_sha
    assert len(sent_messages) == 1

    email_message = sent_messages[0]
    attachments = list(email_message.iter_attachments())
    assert len(attachments) == 1
    assert attachments[0].get_filename() == "note.pdf"
    assert attachments[0].get_content_type() == "application/pdf"
    assert attachments[0].get_payload(decode=True) == attachment_content


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
