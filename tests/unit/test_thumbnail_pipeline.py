"""
Unit tests for thumbnail generation pipeline hardening.

Covers:
  - parse_dimensions: all format variations and edge cases
  - _bbox_from_point: aspect ratio matching with various dimension formats
  - _validate_thumbnail: dimension mismatch and empty band detection
  - create_bbox_from_coordinates: aspect_ratio parameter
"""
import logging
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

from app.services.imagery_service import (
    DEFAULT_CAROUSEL_BBOX_BUFFER_DEGREES,
    ImageryService,
    parse_dimensions,
)
from app.utils.bbox_utils import create_bbox_from_coordinates


# =========================================================================
# TestParseDimensions
# =========================================================================


class TestParseDimensions:
    """Tests for the parse_dimensions pure function."""

    def test_string_width_x_height(self):
        assert parse_dimensions("768x576") == (768, 576)

    def test_string_uppercase_x(self):
        assert parse_dimensions("768X576") == (768, 576)

    def test_string_mixed_case_x(self):
        assert parse_dimensions("1920x1080") == (1920, 1080)

    def test_string_square(self):
        assert parse_dimensions("512") == (512, 512)

    def test_int_square(self):
        assert parse_dimensions(512) == (512, 512)

    def test_float_square(self):
        assert parse_dimensions(1024.0) == (1024, 1024)

    def test_string_with_whitespace(self):
        assert parse_dimensions("  768x576  ") == (768, 576)

    def test_invalid_empty(self):
        with pytest.raises(ValueError):
            parse_dimensions("")

    def test_invalid_no_height(self):
        with pytest.raises(ValueError):
            parse_dimensions("768x")

    def test_invalid_no_width(self):
        with pytest.raises(ValueError):
            parse_dimensions("x576")

    def test_invalid_zero_int(self):
        with pytest.raises(ValueError):
            parse_dimensions(0)

    def test_invalid_negative_int(self):
        with pytest.raises(ValueError):
            parse_dimensions(-100)

    def test_invalid_zero_in_pair(self):
        with pytest.raises(ValueError):
            parse_dimensions("0x576")

    def test_invalid_garbage(self):
        with pytest.raises(ValueError):
            parse_dimensions("not_a_dimension")

    def test_invalid_none(self):
        with pytest.raises(ValueError):
            parse_dimensions(None)


# =========================================================================
# TestBboxFromPoint
# =========================================================================


class TestBboxFromPoint:
    """Tests for _bbox_from_point aspect-ratio matching."""

    @staticmethod
    def _make_service(dimensions="768x576", buffer_deg=DEFAULT_CAROUSEL_BBOX_BUFFER_DEGREES):
        svc = object.__new__(ImageryService)
        svc.db = MagicMock()
        svc._gee = MagicMock()
        svc._storage = MagicMock()
        svc._resolve_thumb_dimensions = MagicMock(return_value=dimensions)
        svc._resolve_bbox_buffer_degrees = MagicMock(return_value=buffer_deg)
        return svc

    def test_default_768x576_aspect_ratio(self):
        """Default 768x576 should produce 4:3 bbox (wider than tall)."""
        svc = self._make_service("768x576", 0.04)
        bbox = svc._bbox_from_point(-27.5, -58.5)

        expected_ar = 768.0 / 576.0
        bbox_w = bbox["east"] - bbox["west"]
        bbox_h = bbox["north"] - bbox["south"]

        assert bbox_w / bbox_h == pytest.approx(expected_ar, rel=1e-6)
        assert bbox_h == pytest.approx(0.08)  # 2 * 0.04

    def test_square_dimension_produces_square_bbox(self):
        """Integer dimension (e.g. 512) should produce square bbox."""
        svc = self._make_service(512, 0.04)
        bbox = svc._bbox_from_point(-30.0, -60.0)

        bbox_w = bbox["east"] - bbox["west"]
        bbox_h = bbox["north"] - bbox["south"]
        assert bbox_w == pytest.approx(bbox_h)

    def test_custom_buffer(self):
        """Explicit buffer_degrees should override the resolved default."""
        svc = self._make_service("768x576")
        bbox = svc._bbox_from_point(-27.5, -58.5, buffer_degrees=0.1)

        bbox_h = bbox["north"] - bbox["south"]
        assert bbox_h == pytest.approx(0.2)  # 2 * 0.1

    def test_wide_dimensions_16_9(self):
        """16:9 dimensions should produce wider bbox."""
        svc = self._make_service("1920x1080", 0.04)
        bbox = svc._bbox_from_point(0.0, 0.0)

        bbox_w = bbox["east"] - bbox["west"]
        bbox_h = bbox["north"] - bbox["south"]
        assert bbox_w / bbox_h == pytest.approx(1920.0 / 1080.0, rel=1e-6)

    def test_bbox_centered_on_point(self):
        """Bbox should be centered on the given lat/lon."""
        svc = self._make_service("768x576", 0.04)
        lat, lon = -35.0, -65.0
        bbox = svc._bbox_from_point(lat, lon)

        center_lat = (bbox["north"] + bbox["south"]) / 2
        center_lon = (bbox["east"] + bbox["west"]) / 2
        assert center_lat == pytest.approx(lat)
        assert center_lon == pytest.approx(lon)

    def test_string_square_dimension(self):
        """String '512' should produce square bbox, same as int 512."""
        svc = self._make_service("512", 0.04)
        bbox = svc._bbox_from_point(-27.0, -58.0)

        bbox_w = bbox["east"] - bbox["west"]
        bbox_h = bbox["north"] - bbox["south"]
        assert bbox_w == pytest.approx(bbox_h)


# =========================================================================
# TestValidateThumbnail
# =========================================================================


class TestValidateThumbnail:
    """Tests for thumbnail post-download validation."""

    @staticmethod
    def _make_service():
        svc = object.__new__(ImageryService)
        svc.db = MagicMock()
        return svc

    @staticmethod
    def _make_png(width, height, color=(100, 150, 200)):
        """Create a solid-color PNG in memory."""
        from PIL import Image as PILImage

        img = PILImage.new("RGB", (width, height), color)
        buf = BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    @staticmethod
    def _make_png_with_empty_bands(width, height):
        """Create PNG with black vertical bands on sides (the bug symptom)."""
        from PIL import Image as PILImage
        from PIL import ImageDraw

        img = PILImage.new("RGB", (width, height), (0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.rectangle([(20, 0), (width - 20, height)], fill=(100, 150, 200))
        buf = BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    def test_valid_dimensions_pass(self):
        svc = self._make_service()
        png = self._make_png(768, 576)
        # Should not raise
        svc._validate_thumbnail(png, "768x576", "RGB", "ep-001")

    def test_dimension_mismatch_raises(self):
        svc = self._make_service()
        png = self._make_png(800, 600)
        with pytest.raises(ValueError, match="dimension mismatch"):
            svc._validate_thumbnail(png, "768x576", "RGB", "ep-001")

    def test_one_pixel_tolerance(self):
        """GEE can be off by 1px; should still pass."""
        svc = self._make_service()
        png = self._make_png(769, 576)
        svc._validate_thumbnail(png, "768x576", "RGB", "ep-001")

    def test_two_pixel_off_raises(self):
        """2px difference exceeds tolerance."""
        svc = self._make_service()
        png = self._make_png(770, 576)
        with pytest.raises(ValueError, match="dimension mismatch"):
            svc._validate_thumbnail(png, "768x576", "RGB", "ep-001")

    def test_empty_bands_logged_as_warning(self, caplog):
        """Empty vertical bands should produce a warning, not a hard failure."""
        svc = self._make_service()
        png = self._make_png_with_empty_bands(768, 576)
        with caplog.at_level(logging.WARNING):
            svc._validate_thumbnail(png, "768x576", "RGB", "ep-001")
        assert "empty" in caplog.text.lower()

    def test_corrupt_bytes_raises(self):
        svc = self._make_service()
        with pytest.raises(ValueError, match="Cannot decode"):
            svc._validate_thumbnail(b"not-an-image", "768x576", "RGB", "ep-001")

    def test_square_dimensions_valid(self):
        svc = self._make_service()
        png = self._make_png(512, 512)
        svc._validate_thumbnail(png, 512, "RGB", "ep-001")


# =========================================================================
# TestCreateBboxFromCoordinates
# =========================================================================


class TestCreateBboxFromCoordinates:
    """Tests for bbox_utils.create_bbox_from_coordinates with aspect_ratio."""

    def test_default_square(self):
        """Default aspect_ratio=1.0 should produce square bbox."""
        bbox = create_bbox_from_coordinates(-27.5, -58.5, buffer_degrees=0.01)
        w = bbox["east"] - bbox["west"]
        h = bbox["north"] - bbox["south"]
        assert w == pytest.approx(h)

    def test_4_3_aspect_ratio(self):
        """aspect_ratio=4/3 should produce wider bbox."""
        ar = 4.0 / 3.0
        bbox = create_bbox_from_coordinates(-27.5, -58.5, buffer_degrees=0.01, aspect_ratio=ar)
        w = bbox["east"] - bbox["west"]
        h = bbox["north"] - bbox["south"]
        assert w / h == pytest.approx(ar, rel=1e-6)

    def test_backward_compatible(self):
        """Calling without aspect_ratio behaves identically to old code."""
        bbox = create_bbox_from_coordinates(-27.5, -58.5, buffer_degrees=0.05)
        assert bbox["west"] == pytest.approx(-58.55)
        assert bbox["east"] == pytest.approx(-58.45)
        assert bbox["south"] == pytest.approx(-27.55)
        assert bbox["north"] == pytest.approx(-27.45)
