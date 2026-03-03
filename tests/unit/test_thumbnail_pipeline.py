"""
Unit tests for thumbnail generation pipeline hardening.

Covers:
  - parse_dimensions: all format variations and edge cases
  - _bbox_from_point: aspect ratio matching with various dimension formats
  - _validate_thumbnail: dimension mismatch and empty band detection
  - create_bbox_from_coordinates: aspect_ratio parameter
  - apply_watermark: output integrity, metadata encoding, feature flags
"""
import logging
import os
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
        assert "low-brightness" in caplog.text.lower()

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

    def test_explicit_square(self):
        """aspect_ratio=1.0 should produce square bbox."""
        bbox = create_bbox_from_coordinates(-27.5, -58.5, buffer_degrees=0.01, aspect_ratio=1.0)
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

    def test_backward_compatible_values(self):
        """With aspect_ratio=1.0, output matches legacy square bbox."""
        bbox = create_bbox_from_coordinates(-27.5, -58.5, buffer_degrees=0.05, aspect_ratio=1.0)
        assert bbox["west"] == pytest.approx(-58.55)
        assert bbox["east"] == pytest.approx(-58.45)
        assert bbox["south"] == pytest.approx(-27.55)
        assert bbox["north"] == pytest.approx(-27.45)

    def test_aspect_ratio_required(self):
        """Omitting aspect_ratio should raise TypeError."""
        with pytest.raises(TypeError):
            create_bbox_from_coordinates(-27.5, -58.5, buffer_degrees=0.01)


# =========================================================================
# TestApplyWatermark
# =========================================================================


class TestApplyWatermark:
    """
    Unit tests for apply_watermark() in app/utils/watermark.py.

    Guards against:
      - Output size collapse (the 2.2 KB all-zeros bug from pixel-loop reconstruction)
      - UnicodeEncodeError in PngInfo.add_text() for non-latin-1 metadata
      - Dimension mutation
      - Silent data destruction (mean brightness check)
    """

    @staticmethod
    def _make_rgb_png(width: int = 768, height: int = 576, color=(100, 150, 60)) -> bytes:
        """Create a solid-color RGB PNG that resembles a GEE satellite thumbnail."""
        from PIL import Image as PILImage

        img = PILImage.new("RGB", (width, height), color)
        buf = BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    @staticmethod
    def _open_bytes(data: bytes):
        from PIL import Image as PILImage

        return PILImage.open(BytesIO(data))

    def test_output_size_and_dimensions_preserved(self):
        """
        apply_watermark() on a valid 768x576 RGB PNG must:
          - Return output between 10 KB and 500 KB.
          - Preserve original pixel dimensions.
          - Produce an image that PIL can re-open.
        """
        from datetime import date

        from app.utils.watermark import apply_watermark

        png = self._make_rgb_png(768, 576)
        result = apply_watermark(png, acquisition_date=date(2026, 2, 8), label="Test")

        assert isinstance(result, bytes)
        assert 10_000 <= len(result) <= 500_000, (
            f"Result size {len(result)} bytes outside expected 10 KB-500 KB range"
        )
        img = self._open_bytes(result)
        assert img.size == (768, 576)

    def test_output_pixels_are_not_all_black(self):
        """
        The watermarked output must not be all-zero (all-black/transparent).
        Guards against pixel-loop reconstruction that silently fills with zeros.
        """
        import numpy as np

        from app.utils.watermark import apply_watermark

        png = self._make_rgb_png(768, 576, color=(100, 150, 60))
        result = apply_watermark(png)

        img = self._open_bytes(result).convert("RGB")
        arr = np.array(img)
        mean_brightness = arr.mean()
        assert mean_brightness > 10.0, (
            f"Mean pixel brightness {mean_brightness:.2f} is suspiciously low; "
            "image may be blank or destroyed"
        )

    def test_non_ascii_metadata_does_not_raise(self):
        """
        Metadata containing non-latin-1 characters (CJK, emoji, accented chars
        outside latin-1) must not raise an exception. This is the direct regression
        test for the original 'argument 2 must be 4-item tuple, not str' error.
        """
        from app.utils.watermark import apply_watermark

        png = self._make_rgb_png()
        metadata = {
            "source": "Sentinel-2",
            "region": "C\u00f3rdoba \u4e2d\u56fd",  # 'Córdoba' + CJK characters
            "label": "Fuego \U0001f525",             # emoji (beyond latin-1)
        }
        result = apply_watermark(png, metadata=metadata)

        assert isinstance(result, bytes)
        assert len(result) > 1_000
        self._open_bytes(result)  # Must be a valid, openable PNG

    def test_disable_watermark_all_returns_original_bytes(self, monkeypatch):
        """
        With DISABLE_WATERMARK_ALL=true, apply_watermark() must return
        exactly the original input bytes unchanged.
        """
        from app.utils.watermark import apply_watermark

        monkeypatch.setenv("DISABLE_WATERMARK_ALL", "true")
        png = self._make_rgb_png()
        result = apply_watermark(png)
        assert result == png

    def test_disable_watermark_logo_still_applies_text(self, monkeypatch):
        """
        With DISABLE_WATERMARK_LOGO=true, text watermark still runs;
        result must be a valid, non-trivial PNG.
        """
        from datetime import date

        from app.utils.watermark import apply_watermark

        monkeypatch.setenv("DISABLE_WATERMARK_LOGO", "true")
        png = self._make_rgb_png()
        result = apply_watermark(png, acquisition_date=date(2026, 1, 15))

        assert isinstance(result, bytes)
        assert len(result) > 10_000
        self._open_bytes(result)

    def test_metadata_with_none_values_skipped(self):
        """
        None values in the metadata dict must be silently skipped,
        not cause a TypeError or AttributeError in add_text().
        """
        from app.utils.watermark import apply_watermark

        png = self._make_rgb_png()
        metadata = {
            "source": "Sentinel-2",
            "cloud_cover": None,
            "label": "Fire",
        }
        result = apply_watermark(png, metadata=metadata)
        assert isinstance(result, bytes)
        assert len(result) > 10_000

    def test_output_passes_pil_verify(self):
        """
        The watermarked output must pass PIL's structural verification
        (no truncated IDAT chunks, no malformed chunk headers).
        """
        from datetime import date

        from PIL import Image as PILImage

        from app.utils.watermark import apply_watermark

        png = self._make_rgb_png()
        result = apply_watermark(
            png,
            acquisition_date=date(2026, 2, 8),
            metadata={"vis_type": "RGB", "satellite": "SENTINEL-2"},
        )
        # verify() raises if PNG is structurally invalid
        PILImage.open(BytesIO(result)).verify()

    def test_pil_unavailable_returns_original(self, monkeypatch):
        """
        When PIL_AVAILABLE is False, apply_watermark() must return
        the original bytes unchanged without raising.
        """
        import app.utils.watermark as wm_module

        monkeypatch.setattr(wm_module, "PIL_AVAILABLE", False)

        from app.utils.watermark import apply_watermark

        dummy = self._make_rgb_png(64, 48)
        result = apply_watermark(dummy)
        assert result == dummy


# =========================================================================
# TestBboxAspectRatioParametrized
# =========================================================================


class TestBboxAspectRatioParametrized:
    """Parametrized aspect ratio tests across multiple dimension configs."""

    @staticmethod
    def _make_service(dimensions, buffer_deg=0.04):
        svc = object.__new__(ImageryService)
        svc.db = MagicMock()
        svc._gee = MagicMock()
        svc._storage = MagicMock()
        svc._resolve_thumb_dimensions = MagicMock(return_value=dimensions)
        svc._resolve_bbox_buffer_degrees = MagicMock(return_value=buffer_deg)
        return svc

    @pytest.mark.parametrize(
        "dimensions, expected_ar",
        [
            ("768x576", 768.0 / 576.0),    # 4:3
            ("1024x768", 1024.0 / 768.0),  # 4:3
            (512, 1.0),                      # square
            ("512", 1.0),                    # square (string)
        ],
        ids=["768x576", "1024x768", "512_int", "512_str"],
    )
    def test_aspect_ratio_matches_dimensions(self, dimensions, expected_ar):
        svc = self._make_service(dimensions)
        bbox = svc._bbox_from_point(-27.5, -58.5)

        bbox_w = bbox["east"] - bbox["west"]
        bbox_h = bbox["north"] - bbox["south"]
        assert bbox_w / bbox_h == pytest.approx(expected_ar, abs=0.01)


# =========================================================================
# TestBlackStripeRegression
# =========================================================================


class TestBlackStripeRegression:
    """Regression test: semi-padding bands (brightness < 10) must be logged."""

    @staticmethod
    def _make_service():
        svc = object.__new__(ImageryService)
        svc.db = MagicMock()
        return svc

    @staticmethod
    def _make_png_with_low_brightness_left_band(width, height):
        """
        Create PNG where the left 20px have RGB=(8,4,4) → mean brightness ~5.33,
        validating the < 10.0 threshold catches semi-padding (not just pure black).
        """
        import numpy as np
        from PIL import Image as PILImage

        arr = np.full((height, width, 3), (100, 150, 200), dtype=np.uint8)
        arr[:, 0:20, :] = (8, 4, 4)  # low-brightness left band
        img = PILImage.fromarray(arr, "RGB")
        buf = BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    def test_low_brightness_left_band_logged(self, caplog):
        """Left band with mean brightness ~5.33 should trigger warning."""
        svc = self._make_service()
        png = self._make_png_with_low_brightness_left_band(768, 576)
        with caplog.at_level(logging.WARNING):
            svc._validate_thumbnail(png, "768x576", "RGB", "ep-regression")
        assert "low-brightness" in caplog.text.lower()
        assert "left" in caplog.text.lower()

    def test_normal_image_no_warning(self, caplog):
        """Uniformly bright image should NOT trigger band warning."""
        from PIL import Image as PILImage

        svc = self._make_service()
        img = PILImage.new("RGB", (768, 576), (100, 150, 200))
        buf = BytesIO()
        img.save(buf, format="PNG")
        png = buf.getvalue()
        with caplog.at_level(logging.WARNING):
            svc._validate_thumbnail(png, "768x576", "RGB", "ep-ok")
        assert "low-brightness" not in caplog.text.lower()
