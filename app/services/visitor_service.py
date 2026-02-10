from datetime import datetime, timedelta


def can_edit_log(
    first_submitted_at: datetime, now: datetime, window_minutes: int = 30
) -> bool:
    """
    Validate whether a visitor log can be edited within a limited window.
    """
    return now <= first_submitted_at + timedelta(minutes=window_minutes)
