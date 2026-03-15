"""
Unit tests for workers.tasks.backfill.recompute_baselines.

Covers:
- Returns done when no events pending.
- Calls _get_baseline_ndvi, updates vegetation_monitoring and fire_events cache, returns ok.
- Handles BaselineNotAvailableError (counts failed, continues).
"""

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from app.services.vae_service import BaselineNotAvailableError

from workers.tasks.backfill import recompute_baselines


def _make_event_row(fire_event_id="e1", start_date=None):
    if start_date is None:
        start_date = date(2024, 6, 15)
    return MagicMock(
        fire_event_id=fire_event_id,
        start_date=start_date,
        bbox_west=-58.5,
        bbox_south=-27.5,
        bbox_east=-58.4,
        bbox_north=-27.4,
    )


@patch("workers.tasks.backfill.SessionLocal")
def test_recompute_baselines_returns_done_when_no_events(mock_session_local):
    """When the events query returns no rows, task returns status done and events_updated 0."""
    mock_db = MagicMock()
    mock_session_local.return_value = mock_db
    mock_db.execute.return_value.fetchall.return_value = []

    result = recompute_baselines(batch_size=50)

    assert result == {"status": "done", "events_updated": 0}
    mock_db.close.assert_called_once()


@patch("workers.tasks.backfill.SessionLocal")
def test_recompute_baselines_calls_get_baseline_and_updates(mock_session_local):
    """When events exist, task calls _get_baseline_ndvi and runs UPDATEs for vm and fire_events."""
    mock_db = MagicMock()
    mock_session_local.return_value = mock_db
    mock_db.execute.return_value.fetchall.return_value = [_make_event_row()]

    mock_vae = MagicMock()
    mock_vae._get_baseline_ndvi.return_value = 0.55

    with patch("app.services.vae_service.VAEService", return_value=mock_vae):
        result = recompute_baselines(batch_size=50)

    assert result["status"] == "ok"
    assert result["events_updated"] == 1
    assert result["events_failed"] == 0
    assert result["events_total"] == 1

    mock_vae._get_baseline_ndvi.assert_called_once()
    call_args = mock_vae._get_baseline_ndvi.call_args[0]
    assert call_args[0] == {
        "west": -58.5,
        "south": -27.5,
        "east": -58.4,
        "north": -27.4,
    }
    assert call_args[1] == date(2024, 6, 15)

    # Two commits: after vm updates, then after fire_events cache
    assert mock_db.commit.call_count == 2
    execute_calls = [
        str(c[0][0]) for c in mock_db.execute.call_args_list if c[0]
    ]
    assert any(
        "vegetation_monitoring" in c and "baseline_ndvi" in c
        for c in execute_calls
    )
    assert any(
        "fire_events" in c and "latest_recovery_status" in c
        for c in execute_calls
    )
    mock_db.close.assert_called_once()


@patch("workers.tasks.backfill.SessionLocal")
def test_recompute_baselines_handles_baseline_not_available_error(mock_session_local):
    """When _get_baseline_ndvi raises BaselineNotAvailableError, event is counted as failed."""
    mock_db = MagicMock()
    mock_session_local.return_value = mock_db
    mock_db.execute.return_value.fetchall.return_value = [_make_event_row()]

    mock_vae = MagicMock()
    mock_vae._get_baseline_ndvi.side_effect = BaselineNotAvailableError("no images")

    with patch("app.services.vae_service.VAEService", return_value=mock_vae):
        result = recompute_baselines(batch_size=50)

    assert result["status"] == "ok"
    assert result["events_updated"] == 0
    assert result["events_failed"] == 1
    assert result["events_total"] == 1
    mock_db.commit.assert_called()
    mock_db.close.assert_called_once()


@patch("workers.tasks.backfill.SessionLocal")
def test_recompute_baselines_handles_generic_exception_per_event(mock_session_local):
    """When _get_baseline_ndvi raises a generic Exception, event is counted as failed."""
    mock_db = MagicMock()
    mock_session_local.return_value = mock_db
    mock_db.execute.return_value.fetchall.return_value = [_make_event_row()]

    mock_vae = MagicMock()
    mock_vae._get_baseline_ndvi.side_effect = RuntimeError("GEE timeout")

    with patch("app.services.vae_service.VAEService", return_value=mock_vae):
        result = recompute_baselines(batch_size=50)

    assert result["status"] == "ok"
    assert result["events_updated"] == 0
    assert result["events_failed"] == 1
    assert result["events_total"] == 1
    mock_db.close.assert_called_once()


@patch("workers.tasks.backfill.SessionLocal")
def test_recompute_baselines_rollback_on_top_level_exception(mock_session_local):
    """When an exception occurs outside the event loop (e.g. commit fails), db.rollback is called."""
    mock_db = MagicMock()
    mock_session_local.return_value = mock_db
    mock_db.execute.return_value.fetchall.return_value = [_make_event_row()]

    mock_vae = MagicMock()
    mock_vae._get_baseline_ndvi.return_value = 0.5
    mock_db.commit.side_effect = RuntimeError("connection lost")

    with patch("app.services.vae_service.VAEService", return_value=mock_vae):
        result = recompute_baselines(batch_size=50)

    assert result["status"] == "error"
    assert "reason" in result
    mock_db.rollback.assert_called_once()
    mock_db.close.assert_called_once()
