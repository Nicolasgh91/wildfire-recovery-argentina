from datetime import datetime, timedelta, timezone

from app.services.visitor_service import can_edit_log


def test_can_edit_log_within_window():
    base = datetime.now(timezone.utc)
    assert can_edit_log(base, base + timedelta(minutes=10)) is True


def test_can_edit_log_outside_window():
    base = datetime.now(timezone.utc)
    assert can_edit_log(base, base + timedelta(minutes=31)) is False
