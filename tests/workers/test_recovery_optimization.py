"""Tests para optimización de backfill (VAE)."""

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from workers.tasks.backfill import (
    SENTINEL2_MIN_COVERAGE_DATE,
    _generate_analysis_points,
)


class TestSentinel2DateFilter:
    """Mejora 1: filtrar puntos pre-cobertura Sentinel-2."""

    def test_no_points_before_sentinel2(self):
        points = _generate_analysis_points(
            date(2014, 6, 1),
            date(2026, 3, 1),
            6,
        )
        assert all(p >= SENTINEL2_MIN_COVERAGE_DATE for p in points)

    def test_event_2015_jan_starts_from_aug(self):
        points = _generate_analysis_points(
            date(2015, 1, 1),
            date(2026, 3, 1),
            6,
        )
        assert points, "Debe generar al menos un punto"
        assert points[0] >= date(2015, 8, 1)

    def test_event_2020_unaffected(self):
        points = _generate_analysis_points(
            date(2020, 1, 1),
            date(2026, 3, 1),
            6,
        )
        # Comportamiento actual: primer semestre completo después del incendio
        assert points[0] == date(2020, 7, 1)
        assert all(p >= SENTINEL2_MIN_COVERAGE_DATE for p in points)

    def test_monthly_regime_also_filtered(self):
        points = _generate_analysis_points(
            date(2015, 3, 1),
            date(2015, 12, 1),
            1,
        )
        assert all(p >= SENTINEL2_MIN_COVERAGE_DATE for p in points)


class TestBaselineFailureSkip:
    """Mejora 2: skip de eventos con baseline fallido."""

    @patch("workers.tasks.recovery.SessionLocal")
    def test_skip_when_baseline_already_failed(self, mock_session_cls):
        """Si ya existe pending con no_baseline_image, retorna skipped.

        Nota: este test depende del orden actual de llamadas a
        `fetchone()` dentro de `analyze_recovery`. Si en el futuro se
        agregan queries intermedias antes del chequeo de baseline
        fallido, el `side_effect` deberá actualizarse.
        """
        mock_db = MagicMock()
        mock_session_cls.return_value = mock_db

        # Simular que el evento existe y luego que ya hay baseline fallido
        mock_db.execute.return_value.fetchone.side_effect = [
            MagicMock(
                start_date=date(2016, 1, 1),
                bbox_west=-60,
                bbox_south=-30,
                bbox_east=-59,
                bbox_north=-29,
            ),
            MagicMock(),  # existing_baseline_failure query → row exists
        ]

        from workers.tasks.recovery import analyze_recovery

        result = analyze_recovery("test-id", "2020-01-01")

        assert result["status"] == "skipped"
        assert result["reason"] == "baseline_already_failed"

