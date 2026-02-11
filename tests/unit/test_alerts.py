from app.core import alerts


def test_send_alert_no_smtp(monkeypatch):
    class DummySettings:
        ALERT_EMAIL = None
        SMTP_HOST = None
        SMTP_PORT = 587
        SMTP_USER = None
        SMTP_PASSWORD = None

    monkeypatch.setattr(alerts, "settings", DummySettings())
    alerts.send_alert("subject", "body")
