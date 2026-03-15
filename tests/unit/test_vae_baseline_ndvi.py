"""
Unit tests for VAEService._get_baseline_ndvi (quality mosaic baseline).

Covers:
- First window (365d) succeeds and returns NDVI mean.
- Fallback to second window (730d) when first returns None or low NDVI.
- Fallback to post-fire window (180-540d) when both pre-fire windows fail.
- BaselineNotAvailableError when all three steps fail.
- Defensive: getInfo() returns None or dict with 'NDVI': None → continue to next window.
"""

from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest

from app.services.vae_service import VAEService, BaselineNotAvailableError


def _make_gee_chain(get_info_returns):
    """Build mock chain: get_sentinel_collection().map().qualityMosaic().select().reduceRegion().getInfo()."""
    if not isinstance(get_info_returns, list):
        get_info_returns = [get_info_returns]
    get_info_mock = MagicMock()
    get_info_mock.side_effect = get_info_returns

    reducer = MagicMock()
    reducer.getInfo = get_info_mock

    select_img = MagicMock()
    select_img.reduceRegion.return_value = reducer

    composite = MagicMock()
    composite.select.return_value = select_img

    ndvi_collection = MagicMock()
    ndvi_collection.qualityMosaic.return_value = composite

    collection = MagicMock()
    collection.map.return_value = ndvi_collection

    return collection


@patch("app.services.vae_service.ee")
@patch("app.services.vae_service.gee_circuit", None)
def test_baseline_ndvi_first_window_succeeds(mock_ee):
    """First window (365d) has valid data; get_sentinel_collection called once with lookback 365."""
    mock_ee.Geometry.Rectangle.return_value = MagicMock()
    mock_ee.Reducer.mean.return_value = MagicMock()

    bbox = {"west": -58.5, "south": -27.5, "east": -58.4, "north": -27.4}
    fire_date = date(2024, 6, 15)

    mock_gee = MagicMock()
    mock_gee.get_sentinel_collection.return_value = _make_gee_chain({"NDVI": 0.62})

    vae = VAEService()
    vae._gee = mock_gee

    result = vae._get_baseline_ndvi(bbox, fire_date)

    assert result == 0.62
    assert mock_gee.get_sentinel_collection.call_count == 1
    call_kw = mock_gee.get_sentinel_collection.call_args[1]
    assert call_kw["start_date"] == fire_date - timedelta(days=365)
    assert call_kw["end_date"] == fire_date - timedelta(days=1)
    assert call_kw["max_cloud_cover"] == 30.0


@patch("app.services.vae_service.ee")
@patch("app.services.vae_service.gee_circuit", None)
def test_baseline_ndvi_fallback_to_730_when_first_window_returns_none(mock_ee):
    """When getInfo() returns None for 365d window, second window (730d) is tried and succeeds."""
    mock_ee.Geometry.Rectangle.return_value = MagicMock()
    mock_ee.Reducer.mean.return_value = MagicMock()

    bbox = {"west": -58.5, "south": -27.5, "east": -58.4, "north": -27.4}
    fire_date = date(2024, 6, 15)

    mock_gee = MagicMock()
    # First call (365d): getInfo returns None (empty composite). Second call (730d): valid NDVI.
    mock_gee.get_sentinel_collection.return_value = _make_gee_chain([None, {"NDVI": 0.55}])

    vae = VAEService()
    vae._gee = mock_gee

    result = vae._get_baseline_ndvi(bbox, fire_date)

    assert result == 0.55
    assert mock_gee.get_sentinel_collection.call_count == 2
    first_start = mock_gee.get_sentinel_collection.call_args_list[0][1]["start_date"]
    second_start = mock_gee.get_sentinel_collection.call_args_list[1][1]["start_date"]
    assert first_start == fire_date - timedelta(days=365)
    assert second_start == fire_date - timedelta(days=730)


@patch("app.services.vae_service.ee")
@patch("app.services.vae_service.gee_circuit", None)
def test_baseline_ndvi_fallback_when_first_window_returns_low_ndvi(mock_ee):
    """When first window returns NDVI < 0.05, second window is tried and succeeds."""
    mock_ee.Geometry.Rectangle.return_value = MagicMock()
    mock_ee.Reducer.mean.return_value = MagicMock()

    bbox = {"west": -58.5, "south": -27.5, "east": -58.4, "north": -27.4}
    fire_date = date(2024, 6, 15)

    mock_gee = MagicMock()
    mock_gee.get_sentinel_collection.return_value = _make_gee_chain(
        [{"NDVI": 0.02}, {"NDVI": 0.58}]
    )

    vae = VAEService()
    vae._gee = mock_gee

    result = vae._get_baseline_ndvi(bbox, fire_date)

    assert result == 0.58
    assert mock_gee.get_sentinel_collection.call_count == 2


@patch("app.services.vae_service.ee")
@patch("app.services.vae_service.gee_circuit", None)
def test_baseline_ndvi_defensive_getinfo_returns_ndvi_none(mock_ee):
    """When getInfo() returns dict with 'NDVI': None (empty composite), continue to next window."""
    mock_ee.Geometry.Rectangle.return_value = MagicMock()
    mock_ee.Reducer.mean.return_value = MagicMock()

    bbox = {"west": -58.5, "south": -27.5, "east": -58.4, "north": -27.4}
    fire_date = date(2024, 6, 15)

    mock_gee = MagicMock()
    mock_gee.get_sentinel_collection.return_value = _make_gee_chain(
        [{"NDVI": None}, {"NDVI": 0.51}]
    )

    vae = VAEService()
    vae._gee = mock_gee

    result = vae._get_baseline_ndvi(bbox, fire_date)

    assert result == 0.51
    assert mock_gee.get_sentinel_collection.call_count == 2


@patch("app.services.vae_service.ee")
@patch("app.services.vae_service.gee_circuit", None)
def test_baseline_ndvi_raises_when_all_three_steps_fail(mock_ee):
    """When 365d, 730d and post-fire (180-540d) all fail, BaselineNotAvailableError is raised."""
    mock_ee.Geometry.Rectangle.return_value = MagicMock()
    mock_ee.Reducer.mean.return_value = MagicMock()

    bbox = {"west": -58.5, "south": -27.5, "east": -58.4, "north": -27.4}
    fire_date = date(2024, 6, 15)

    mock_gee = MagicMock()
    # Pre 365d: None; pre 730d: None; post 180-540d: low NDVI (below 0.1 threshold)
    mock_gee.get_sentinel_collection.return_value = _make_gee_chain(
        [None, {"NDVI": None}, {"NDVI": 0.05}]
    )

    vae = VAEService()
    vae._gee = mock_gee

    with pytest.raises(BaselineNotAvailableError) as exc_info:
        vae._get_baseline_ndvi(bbox, fire_date)

    assert str(fire_date) in str(exc_info.value)
    assert "post-180-540d" in str(exc_info.value)
    assert mock_gee.get_sentinel_collection.call_count == 3
    # Third call is post-fire window
    third_call_kw = mock_gee.get_sentinel_collection.call_args_list[2][1]
    assert third_call_kw["start_date"] == fire_date + timedelta(days=180)
    assert third_call_kw["end_date"] == fire_date + timedelta(days=540)


@patch("app.services.vae_service.ee")
@patch("app.services.vae_service.gee_circuit", None)
def test_baseline_ndvi_post_fire_fallback_succeeds(mock_ee):
    """When both pre-fire windows fail, post-fire (180-540d) fallback succeeds with NDVI >= 0.1."""
    mock_ee.Geometry.Rectangle.return_value = MagicMock()
    mock_ee.Reducer.mean.return_value = MagicMock()

    bbox = {"west": -58.5, "south": -27.5, "east": -58.4, "north": -27.4}
    fire_date = date(2015, 3, 1)  # Pre-Sentinel-2 era

    mock_gee = MagicMock()
    # Pre 365d and 730d fail; post-fire returns valid NDVI
    mock_gee.get_sentinel_collection.return_value = _make_gee_chain(
        [None, {"NDVI": None}, {"NDVI": 0.48}]
    )

    vae = VAEService()
    vae._gee = mock_gee

    result = vae._get_baseline_ndvi(bbox, fire_date)

    assert result == 0.48
    assert mock_gee.get_sentinel_collection.call_count == 3
    third_call_kw = mock_gee.get_sentinel_collection.call_args_list[2][1]
    assert third_call_kw["start_date"] == fire_date + timedelta(days=180)
    assert third_call_kw["end_date"] == fire_date + timedelta(days=540)


@patch("app.services.vae_service.ee")
@patch("app.services.vae_service.gee_circuit", None)
def test_baseline_ndvi_uses_ndvi_key_not_ndvi_mean(mock_ee):
    """Reducer.mean() on band 'NDVI' yields key 'NDVI'; ensure we read it."""
    mock_ee.Geometry.Rectangle.return_value = MagicMock()
    mock_ee.Reducer.mean.return_value = MagicMock()

    bbox = {"west": -58.5, "south": -27.5, "east": -58.4, "north": -27.4}
    fire_date = date(2024, 6, 15)

    mock_gee = MagicMock()
    # Only 'NDVI' key (no 'NDVI_mean')
    mock_gee.get_sentinel_collection.return_value = _make_gee_chain({"NDVI": 0.44})

    vae = VAEService()
    vae._gee = mock_gee

    result = vae._get_baseline_ndvi(bbox, fire_date)

    assert result == 0.44


@patch("app.services.vae_service.ee")
@patch("app.services.vae_service.gee_circuit", None)
def test_baseline_ndvi_accepts_optional_lookback_and_cloud_cover(mock_ee):
    """Optional lookback_days and max_cloud_cover are passed to get_sentinel_collection."""
    mock_ee.Geometry.Rectangle.return_value = MagicMock()
    mock_ee.Reducer.mean.return_value = MagicMock()

    bbox = {"west": -58.5, "south": -27.5, "east": -58.4, "north": -27.4}
    fire_date = date(2024, 6, 15)

    mock_gee = MagicMock()
    mock_gee.get_sentinel_collection.return_value = _make_gee_chain({"NDVI": 0.5})

    vae = VAEService()
    vae._gee = mock_gee

    vae._get_baseline_ndvi(
        bbox, fire_date, lookback_days=180, max_cloud_cover=20.0
    )

    call_kw = mock_gee.get_sentinel_collection.call_args[1]
    assert call_kw["start_date"] == fire_date - timedelta(days=180)
    assert call_kw["max_cloud_cover"] == 20.0
