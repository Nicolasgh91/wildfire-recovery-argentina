"""
Tests for episode bbox aggregation logic.

Verifies that update_episode_metrics() uses perimeter-based spatial functions
(ST_XMin/ST_YMin/ST_XMax/ST_YMax on fe.perimeter) instead of centroid-based
point functions (ST_X/ST_Y on fe.centroid).

Test approach: substring matching on the SQL query text, NOT exact string
comparison. This avoids fragile tests that break on whitespace/formatting changes.
"""
import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from uuid import uuid4

from app.services.episode_service import EpisodeService


class TestBBoxAggregationSQL:
    """Verify the SQL query in update_episode_metrics uses perimeter geometry."""

    def _capture_sql(self):
        """
        Create a mock EpisodeService and capture the SQL text sent to db.execute.

        Returns the raw SQL string from the first db.execute call that contains
        'bbox_minx' (the aggregation query).
        """
        svc = EpisodeService.__new__(EpisodeService)
        mock_db = MagicMock()
        svc.db = mock_db

        # First call: existing episode lookup
        existing_result = MagicMock()
        existing_result.first.return_value = {
            "status": "active",
            "end_date": None,
            "last_seen_at": None,
            "extinct_at": None,
        }

        # Second call: aggregation query
        agg_result = MagicMock()
        agg_result.first.return_value = None  # triggers early return (no events)

        mock_db.execute.return_value.mappings.side_effect = [
            existing_result,
            agg_result,
        ]

        episode_id = uuid4()
        version_id = uuid4()

        svc.update_episode_metrics(
            episode_id,
            clustering_version_id=version_id,
            min_points=2,
        )

        # Find the call containing the aggregation SQL
        for call_args in mock_db.execute.call_args_list:
            sql_obj = call_args[0][0]
            sql_text = str(sql_obj.text) if hasattr(sql_obj, "text") else str(sql_obj)
            if "bbox_minx" in sql_text:
                return sql_text

        pytest.fail("No SQL call containing 'bbox_minx' was captured")

    def test_bbox_uses_perimeter_xmin(self):
        """bbox_minx must be derived from ST_XMin(fe.perimeter), not centroid."""
        sql = self._capture_sql()
        assert "ST_XMin(fe.perimeter::geometry)" in sql, (
            f"Expected ST_XMin(fe.perimeter::geometry) in SQL, got:\n{sql}"
        )

    def test_bbox_uses_perimeter_ymin(self):
        """bbox_miny must be derived from ST_YMin(fe.perimeter), not centroid."""
        sql = self._capture_sql()
        assert "ST_YMin(fe.perimeter::geometry)" in sql, (
            f"Expected ST_YMin(fe.perimeter::geometry) in SQL, got:\n{sql}"
        )

    def test_bbox_uses_perimeter_xmax(self):
        """bbox_maxx must be derived from ST_XMax(fe.perimeter), not centroid."""
        sql = self._capture_sql()
        assert "ST_XMax(fe.perimeter::geometry)" in sql, (
            f"Expected ST_XMax(fe.perimeter::geometry) in SQL, got:\n{sql}"
        )

    def test_bbox_uses_perimeter_ymax(self):
        """bbox_maxy must be derived from ST_YMax(fe.perimeter), not centroid."""
        sql = self._capture_sql()
        assert "ST_YMax(fe.perimeter::geometry)" in sql, (
            f"Expected ST_YMax(fe.perimeter::geometry) in SQL, got:\n{sql}"
        )

    def test_bbox_does_not_use_centroid_for_bounds(self):
        """bbox must NOT use ST_X(fe.centroid) or ST_Y(fe.centroid) for bounds."""
        sql = self._capture_sql()

        # Centroid is still valid for centroid_lat/centroid_lon (AVG),
        # but should NOT appear in MIN/MAX bbox calculations.
        # Check that centroid is not used in the specific bbox context.
        for bad_pattern in [
            "MIN(ST_X(fe.centroid",
            "MAX(ST_X(fe.centroid",
            "MIN(ST_Y(fe.centroid",
            "MAX(ST_Y(fe.centroid",
        ]:
            assert bad_pattern not in sql, (
                f"Found centroid-based bbox pattern '{bad_pattern}' in SQL:\n{sql}"
            )


class TestBBoxNullPerimeterFallback:
    """Verify that NULL perimeter bbox falls back to centroid coordinates."""

    def test_null_bbox_falls_back_to_centroid(self):
        """When perimeter bbox values are NULL, centroid coords are used."""
        svc = EpisodeService.__new__(EpisodeService)
        mock_db = MagicMock()
        svc.db = mock_db

        # Stub _resolve_inactive_grace_hours to avoid DB lookup
        svc._episode_flow_params_cache = {"episode_temporal_window_hours": 720}

        centroid_lat = -34.5
        centroid_lon = -58.5

        existing_result = MagicMock()
        existing_result.first.return_value = {
            "status": "active",
            "end_date": None,
            "last_seen_at": None,
            "extinct_at": None,
        }

        from datetime import datetime, timezone

        agg_row = {
            "start_date": datetime(2026, 1, 1, tzinfo=timezone.utc),
            "last_seen_at": datetime(2026, 1, 2, tzinfo=timezone.utc),
            "event_count": 1,
            "detection_count": 5,
            "frp_sum": 100.0,
            "frp_max": 50.0,
            "estimated_area_hectares": 10.0,
            "provinces": ["Buenos Aires"],
            "statuses": ["active"],
            "centroid_lat": centroid_lat,
            "centroid_lon": centroid_lon,
            # Perimeter-based bbox is NULL (event has no perimeter)
            "bbox_minx": None,
            "bbox_miny": None,
            "bbox_maxx": None,
            "bbox_maxy": None,
        }

        agg_result = MagicMock()
        agg_result.first.return_value = agg_row

        mock_db.execute.return_value.mappings.side_effect = [
            existing_result,
            agg_result,
        ]

        episode_id = uuid4()
        version_id = uuid4()

        svc.update_episode_metrics(
            episode_id,
            clustering_version_id=version_id,
            min_points=1,
        )

        # The UPDATE call is the third db.execute call
        update_call = mock_db.execute.call_args_list[2]
        params = update_call[0][1]

        assert params["bbox_minx"] == centroid_lon, (
            f"Expected bbox_minx={centroid_lon}, got {params['bbox_minx']}"
        )
        assert params["bbox_miny"] == centroid_lat, (
            f"Expected bbox_miny={centroid_lat}, got {params['bbox_miny']}"
        )
        assert params["bbox_maxx"] == centroid_lon, (
            f"Expected bbox_maxx={centroid_lon}, got {params['bbox_maxx']}"
        )
        assert params["bbox_maxy"] == centroid_lat, (
            f"Expected bbox_maxy={centroid_lat}, got {params['bbox_maxy']}"
        )

    def test_valid_bbox_is_preserved(self):
        """When perimeter bbox values are present, they are used as-is."""
        svc = EpisodeService.__new__(EpisodeService)
        mock_db = MagicMock()
        svc.db = mock_db

        svc._episode_flow_params_cache = {"episode_temporal_window_hours": 720}

        from datetime import datetime, timezone

        agg_row = {
            "start_date": datetime(2026, 1, 1, tzinfo=timezone.utc),
            "last_seen_at": datetime(2026, 1, 2, tzinfo=timezone.utc),
            "event_count": 2,
            "detection_count": 20,
            "frp_sum": 200.0,
            "frp_max": 80.0,
            "estimated_area_hectares": 116.0,
            "provinces": ["Córdoba"],
            "statuses": ["active"],
            "centroid_lat": -31.0,
            "centroid_lon": -64.0,
            # Real perimeter-based bbox
            "bbox_minx": -64.05,
            "bbox_miny": -31.04,
            "bbox_maxx": -63.95,
            "bbox_maxy": -30.96,
        }

        existing_result = MagicMock()
        existing_result.first.return_value = {
            "status": "active",
            "end_date": None,
            "last_seen_at": None,
            "extinct_at": None,
        }

        agg_result = MagicMock()
        agg_result.first.return_value = agg_row

        mock_db.execute.return_value.mappings.side_effect = [
            existing_result,
            agg_result,
        ]

        episode_id = uuid4()
        version_id = uuid4()

        svc.update_episode_metrics(
            episode_id,
            clustering_version_id=version_id,
            min_points=1,
        )

        update_call = mock_db.execute.call_args_list[2]
        params = update_call[0][1]

        assert params["bbox_minx"] == -64.05
        assert params["bbox_miny"] == -31.04
        assert params["bbox_maxx"] == -63.95
        assert params["bbox_maxy"] == -30.96
