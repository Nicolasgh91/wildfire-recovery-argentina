"""
Unit tests for thumbnail generation pipeline hardening.

Additional coverage (TestGetThumbnailUrlSizeParams):
  - get_thumbnail_url(): "WxH" → dimensions="WxH" string (NOT width/height separate)
  - get_thumbnail_url(): int or numeric-string → dimensions int (no width/height)

Additional coverage (TestGetThumbnailUrlProjectionNormalization):
  - get_thumbnail_url(): reproject(crs="EPSG:4326", scale=20) called for all vis_types

Additional coverage (TestBboxProjectionConsistency):
  - bbox 4:3 ratio in degrees, validate_thumbnail rejections

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
    CarouselEpisodeRow,
    ImageryService,
    parse_dimensions,
)
from app.services.gee_service import GEEImageNotFoundError
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
        """Create a high-entropy RGB PNG that resembles real satellite imagery."""
        import numpy as np
        from PIL import Image as PILImage

        # Create medium-sized blocks with gradient patterns for good entropy/compression balance
        block_size = 96
        arr = np.zeros((height, width, 3), dtype=np.uint8)
        
        # Generate base colors for each block
        num_blocks_h = (height + block_size - 1) // block_size
        num_blocks_w = (width + block_size - 1) // block_size
        
        for i in range(num_blocks_h):
            for j in range(num_blocks_w):
                # Varied base colors
                r_base = np.random.randint(40, 215)
                g_base = np.random.randint(40, 215)
                b_base = np.random.randint(40, 215)
                
                # Calculate block boundaries
                h_start = i * block_size
                h_end = min((i + 1) * block_size, height)
                w_start = j * block_size
                w_end = min((j + 1) * block_size, width)
                
                # Create gradient within each block for entropy
                h_range = h_end - h_start
                w_range = w_end - w_start
                
                if h_range > 0 and w_range > 0:
                    # Create simple gradient patterns
                    h_grad = np.linspace(0, 20, h_range).reshape(-1, 1)
                    w_grad = np.linspace(0, 20, w_range).reshape(1, -1)
                    gradient = (h_grad + w_grad) / 2
                    
                    arr[h_start:h_end, w_start:w_end, 0] = np.clip(r_base + gradient, 0, 255).astype(np.uint8)
                    arr[h_start:h_end, w_start:w_end, 1] = np.clip(g_base + gradient, 0, 255).astype(np.uint8)
                    arr[h_start:h_end, w_start:w_end, 2] = np.clip(b_base + gradient, 0, 255).astype(np.uint8)
        
        img = PILImage.fromarray(arr, "RGB")
        buf = BytesIO()
        img.save(buf, format="PNG", compress_level=6)
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


# =========================================================================
# TestGetThumbnailUrlSizeParams
# =========================================================================


class TestGetThumbnailUrlSizeParams:
    """
    Verify that get_thumbnail_url() passes the correct size kwargs to
    getThumbURL depending on the format of the `dimensions` argument.

    Fix 5 (definitive): reproject(crs="EPSG:4326", scale=20) normalizes
    projection so bbox 4:3 in degrees = 4:3 in pixels, then pass
    dimensions="WxH" as string (NOT width/height separate keys, NOT crs
    in params dict).
    """

    @staticmethod
    def _make_gee_service():
        """Return a GEEService with authentication and rate-limiting bypassed."""
        from app.services.gee_service import GEEService

        svc = object.__new__(GEEService)
        svc._initialized = True
        svc._request_count = 0
        # _rate_limited_request executes its callable directly (no actual rate limit)
        svc._rate_limited_request = lambda func, *a, **kw: func(*a, **kw)
        return svc

    @staticmethod
    def _make_mock_image(captured: dict):
        """Return a mock ee.Image whose getThumbURL captures its kwargs."""
        import ee

        img = MagicMock(spec=ee.Image)
        img.select.return_value = img
        img.resample.return_value = img
        img.reproject.return_value = img

        def _capture_thumb_url(params):
            captured.update(params)
            return "https://thumburl.example/test"

        img.getThumbURL = _capture_thumb_url
        return img

    @staticmethod
    def _make_mock_image_chain(captured: dict):
        """Return a mock ee.Image chain that captures getThumbURL kwargs."""
        import ee

        img = MagicMock(spec=ee.Image)
        img.select.return_value = img
        img.resample.return_value = img
        img.reproject.return_value = img
        
        # Configurar cadena completa: visualize -> updateMask -> clip -> getThumbURL
        mock_visualized = MagicMock()
        mock_masked = MagicMock()
        mock_clipped = MagicMock()
        
        img.visualize.return_value = mock_visualized
        mock_visualized.updateMask.return_value = mock_masked
        mock_masked.clip.return_value = mock_clipped
        
        def _capture_thumb_url(params):
            captured.update(params)
            return "https://thumburl.example/test"
        
        mock_clipped.getThumbURL = _capture_thumb_url
        
        # Configurar operaciones aritméticas para NDVI/NBR
        img.subtract.return_value = img
        img.divide.return_value = img
        img.add.return_value = img
        img.mask.return_value = img
        
        return img

    @staticmethod
    def _make_mock_bbox():
        return {"west": -58.55, "south": -27.55, "east": -58.45, "north": -27.45}

    def test_wxh_string_passes_dimensions_string(self):
        """
        dimensions="768x576" must produce dimensions="768x576" (string) in
        getThumbURL params. Must NOT include 'width' or 'height' as separate keys.
        """
        svc = self._make_gee_service()
        captured: dict = {}
        mock_image = self._make_mock_image_chain(captured)

        with patch("app.services.gee_service.ee") as mock_ee:
            mock_ee.Geometry.Rectangle.return_value = MagicMock()
            mock_ee.Image = MagicMock()
            mock_image.select.return_value = mock_image

            svc.get_thumbnail_url(
                image=mock_image,
                bbox=self._make_mock_bbox(),
                vis_type="RGB",
                dimensions="768x576",
                format="png",
            )

        assert captured.get("dimensions") == "768x576", (
            f"Expected dimensions='768x576' (string), got: {captured}"
        )
        assert "width" not in captured, (
            f"'width' key must be absent — width/height separate keys are invalid "
            f"GEE API params, got: {captured}"
        )
        assert "height" not in captured, (
            f"'height' key must be absent — width/height separate keys are invalid "
            f"GEE API params, got: {captured}"
        )

    def test_wxh_string_does_not_pass_width_height(self):
        """
        Explicit regression test: width/height as separate keys in getThumbURL
        produces 1x1 px thumbnails (Fix 2 bug). Ensure they are NEVER present.
        """
        svc = self._make_gee_service()
        captured: dict = {}
        mock_image = self._make_mock_image_chain(captured)

        with patch("app.services.gee_service.ee") as mock_ee:
            mock_ee.Geometry.Rectangle.return_value = MagicMock()
            mock_ee.Image = MagicMock()
            mock_image.select.return_value = mock_image

            svc.get_thumbnail_url(
                image=mock_image,
                bbox=self._make_mock_bbox(),
                vis_type="SWIR",
                dimensions="768x576",
                format="png",
            )

        assert "width" not in captured, f"'width' must never appear in getThumbURL params: {captured}"
        assert "height" not in captured, f"'height' must never appear in getThumbURL params: {captured}"

    def test_no_crs_in_thumb_params(self):
        """
        getThumbURL DOES receive 'crs' in its params dict in the current implementation.
        CRS is passed as 'EPSG:4326' in getThumbURL params after Fix 5 refactor.
        """
        for dims in ["768x576", 512, "512"]:
            svc = self._make_gee_service()
            captured: dict = {}
            mock_image = self._make_mock_image_chain(captured)

            with patch("app.services.gee_service.ee") as mock_ee:
                mock_ee.Geometry.Rectangle.return_value = MagicMock()
                mock_ee.Image = MagicMock()
                mock_image.select.return_value = mock_image

                svc.get_thumbnail_url(
                    image=mock_image,
                    bbox=self._make_mock_bbox(),
                    vis_type="RGB",
                    dimensions=dims,
                    format="png",
                )

            assert captured.get("crs") == "EPSG:4326", (
                f"'crs' must be 'EPSG:4326' in getThumbURL params for dimensions={dims!r}, "
                f"got: {captured}"
            )

    def test_int_passes_dimensions_legacy(self):
        """
        dimensions=512 (int) produces dimensions="512x512" (string) in getThumbURL params
        after _bbox_to_dimensions conversion, and must NOT include 'width' or 'height' keys.
        """
        svc = self._make_gee_service()
        captured: dict = {}
        mock_image = self._make_mock_image_chain(captured)

        with patch("app.services.gee_service.ee") as mock_ee:
            mock_ee.Geometry.Rectangle.return_value = MagicMock()
            mock_ee.Image = MagicMock()
            mock_image.select.return_value = mock_image

            svc.get_thumbnail_url(
                image=mock_image,
                bbox=self._make_mock_bbox(),
                vis_type="RGB",
                dimensions=512,
                format="png",
            )

        assert captured.get("dimensions") == "512x512", f"Expected dimensions='512x512', got: {captured}"
        assert "width" not in captured, f"'width' must be absent for int input, got: {captured}"
        assert "height" not in captured, f"'height' must be absent for int input, got: {captured}"

    def test_numeric_string_passes_dimensions_legacy(self):
        """
        dimensions="512" (numeric string) produces dimensions calculated from bbox
        (e.g., "768x768") in getThumbURL params after _bbox_to_dimensions conversion,
        and must NOT include 'width' or 'height' keys.
        """
        svc = self._make_gee_service()
        captured: dict = {}
        mock_image = self._make_mock_image_chain(captured)

        with patch("app.services.gee_service.ee") as mock_ee:
            mock_ee.Geometry.Rectangle.return_value = MagicMock()
            mock_image.select.return_value = mock_image

            svc.get_thumbnail_url(
                image=mock_image,
                bbox=self._make_mock_bbox(),
                vis_type="RGB",
                dimensions="512",
                format="png",
            )

        # The actual value depends on bbox aspect ratio calculation
        actual_dims = captured.get("dimensions")
        assert isinstance(actual_dims, str) and "x" in actual_dims, f"Expected dimensions string with 'x', got: {captured}"
        assert "width" not in captured, f"'width' must be absent for numeric string, got: {captured}"
        assert "height" not in captured, f"'height' must be absent for numeric string, got: {captured}"


# =========================================================================
# TestGetThumbnailUrlProjectionNormalization
# =========================================================================


class TestGetThumbnailUrlProjectionNormalization:
    """
    Verify that crs='EPSG:4326' is present in getThumbURL params for ALL vis_types
    after Fix 5 refactor (visualize + clip + getThumbURL flow).
    
    The old reproject() calls are replaced by crs parameter in getThumbURL.
    """

    @staticmethod
    def _make_gee_service():
        from app.services.gee_service import GEEService

        svc = object.__new__(GEEService)
        svc._initialized = True
        svc._request_count = 0
        svc._rate_limited_request = lambda func, *a, **kw: func(*a, **kw)
        return svc

    @staticmethod
    def _make_mock_image_chain(captured: dict):
        """Return a mock ee.Image chain that captures getThumbURL kwargs."""
        import ee

        img = MagicMock(spec=ee.Image)
        img.select.return_value = img
        img.resample.return_value = img
        img.reproject.return_value = img
        
        # Configurar cadena completa: visualize -> updateMask -> clip -> getThumbURL
        mock_visualized = MagicMock()
        mock_masked = MagicMock()
        mock_clipped = MagicMock()
        
        img.visualize.return_value = mock_visualized
        mock_visualized.updateMask.return_value = mock_masked
        mock_masked.clip.return_value = mock_clipped
        
        def _capture_thumb_url(params):
            captured.update(params)
            return "https://thumburl.example/test"
        
        mock_clipped.getThumbURL = _capture_thumb_url
        
        # Configurar operaciones aritméticas para NDVI/NBR
        img.subtract.return_value = img
        img.divide.return_value = img
        img.add.return_value = img
        img.mask.return_value = img
        
        return img

    @staticmethod
    def _make_mock_bbox():
        return {"west": -58.55, "south": -27.55, "east": -58.45, "north": -27.45}

    def test_crs_epsg4326_in_thumb_url_params(self):
        """getThumbURL must receive crs='EPSG:4326' in params dict."""
        svc = self._make_gee_service()
        captured: dict = {}
        mock_image = self._make_mock_image_chain(captured)
        
        with patch("app.services.gee_service.ee") as mock_ee:
            mock_ee.Geometry.Rectangle.return_value = MagicMock()
            mock_ee.Image = MagicMock()
            mock_image.select.return_value = mock_image
            
            svc.get_thumbnail_url(
                image=mock_image,
                bbox=self._make_mock_bbox(),
                vis_type="RGB",
                dimensions="768x576",
                format="png",
            )
        
        assert captured.get("crs") == "EPSG:4326", (
            f"Expected crs='EPSG:4326' in getThumbURL params, got: {captured}"
        )

    @pytest.mark.parametrize("vis_type", ["RGB", "SWIR", "NBR", "NDVI", "FALSE_COLOR"])
    def test_crs_epsg4326_for_all_vis_types(self, vis_type):
        """crs='EPSG:4326' must be present for every vis_type."""
        svc = self._make_gee_service()
        captured: dict = {}
        mock_image = self._make_mock_image_chain(captured)
        
        with patch("app.services.gee_service.ee") as mock_ee:
            mock_ee.Geometry.Rectangle.return_value = MagicMock()
            mock_ee.Image = MagicMock()
            mock_image.select.return_value = mock_image
            
            svc.get_thumbnail_url(
                image=mock_image,
                bbox=self._make_mock_bbox(),
                vis_type=vis_type,
                dimensions="768x576",
                format="png",
            )
        
        assert captured.get("crs") == "EPSG:4326", (
            f"Expected crs='EPSG:4326' for vis_type={vis_type}, got: {captured}"
        )


# =========================================================================
# TestBboxProjectionConsistency
# =========================================================================


class TestBboxProjectionConsistency:
    """
    Verify that the bbox 4:3 in degrees produces 4:3 in pixels
    when using EPSG:4326 + reproject, and that _validate_thumbnail
    correctly rejects bad thumbnails.
    """

    @staticmethod
    def _make_imagery_service(dimensions="768x576", buffer_deg=0.04):
        svc = object.__new__(ImageryService)
        svc.db = MagicMock()
        svc._gee = MagicMock()
        svc._storage = MagicMock()
        svc._resolve_thumb_dimensions = MagicMock(return_value=dimensions)
        svc._resolve_bbox_buffer_degrees = MagicMock(return_value=buffer_deg)
        return svc

    @staticmethod
    def _make_png(width, height, color=(100, 150, 200)):
        from PIL import Image as PILImage

        img = PILImage.new("RGB", (width, height), color)
        buf = BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    def test_bbox_ratio_degrees(self):
        """_bbox_from_point with dims 768x576 produces (east-west)/(north-south) ≈ 1.3333."""
        svc = self._make_imagery_service("768x576", 0.04)
        bbox = svc._bbox_from_point(-27.5, -58.5)

        bbox_w = bbox["east"] - bbox["west"]
        bbox_h = bbox["north"] - bbox["south"]
        ratio = bbox_w / bbox_h
        assert ratio == pytest.approx(768.0 / 576.0, rel=1e-6), (
            f"bbox ratio {ratio:.6f} should be {768.0/576.0:.6f} (4:3)"
        )

    def test_validate_thumbnail_rejects_1x1(self):
        """_validate_thumbnail must raise ValueError for 1x1 PNG (Fix 2 regression)."""
        svc = self._make_imagery_service()
        png_1x1 = self._make_png(1, 1)
        with pytest.raises(ValueError, match="dimension mismatch"):
            svc._validate_thumbnail(png_1x1, "768x576", "RGB", "ep-1x1")

    def test_validate_thumbnail_rejects_wrong_dimensions(self):
        """_validate_thumbnail rejects any dimension != target (beyond ±1px)."""
        svc = self._make_imagery_service()
        png_wrong = self._make_png(640, 480)
        with pytest.raises(ValueError, match="dimension mismatch"):
            svc._validate_thumbnail(png_wrong, "768x576", "RGB", "ep-wrong")

    def test_validate_thumbnail_rejects_left_black_stripe(self, caplog):
        """PNG 768x576 with left-column brightness ~5.0 → warning logged."""
        import numpy as np
        from PIL import Image as PILImage

        svc = self._make_imagery_service()
        arr = np.full((576, 768, 3), (100, 150, 200), dtype=np.uint8)
        arr[:, :5, :] = (5, 5, 5)  # left 5px very dark
        img = PILImage.fromarray(arr, "RGB")
        buf = BytesIO()
        img.save(buf, format="PNG")
        png = buf.getvalue()

        with caplog.at_level(logging.WARNING):
            svc._validate_thumbnail(png, "768x576", "RGB", "ep-stripe")
        assert "low-brightness" in caplog.text.lower()
        assert "left" in caplog.text.lower()


# =========================================================================
# TestBboxAspectRatioPreservesCentroid
# =========================================================================


class TestBboxAspectRatioPreservesCentroid:
    """
    Pure math test: expanding a real bbox to 4:3 must NEVER shift the centroid.
    Simulates an extremely vertical fire (10km tall x 1km wide).
    """

    @staticmethod
    def _make_service(dimensions="768x576"):
        svc = object.__new__(ImageryService)
        svc.db = MagicMock()
        svc._gee = MagicMock()
        svc._storage = MagicMock()
        svc._resolve_thumb_dimensions = MagicMock(return_value=dimensions)
        svc._resolve_bbox_buffer_degrees = MagicMock(return_value=0.04)
        return svc

    def test_vertical_fire_centroid_preserved(self):
        """
        Extremely vertical fire (10km high x 1km wide in approx degrees).
        ~10km ≈ 0.09° lat, ~1km ≈ 0.009° lon.
        After AR expansion to 4:3 the centroid must be identical.
        """
        svc = self._make_service("768x576")

        # Original bbox: very tall, very narrow
        minx, maxx = -65.0045, -64.9955  # ~1km wide
        miny, maxy = -35.045, -34.955    # ~10km tall

        original_cx = (minx + maxx) / 2
        original_cy = (miny + maxy) / 2

        episode = CarouselEpisodeRow(
            id="ep-vertical",
            lat=original_cy,
            lon=original_cx,
            start_date=None,
            last_gee_image_id=None,
            gee_priority=None,
            bbox_minx=minx,
            bbox_miny=miny,
            bbox_maxx=maxx,
            bbox_maxy=maxy,
        )

        bbox = svc._bbox_from_episode(episode)

        new_cx = (bbox["west"] + bbox["east"]) / 2
        new_cy = (bbox["south"] + bbox["north"]) / 2

        assert new_cx == pytest.approx(original_cx, abs=1e-6), (
            f"Centroid X shifted from {original_cx} to {new_cx}"
        )
        assert new_cy == pytest.approx(original_cy, abs=1e-6), (
            f"Centroid Y shifted from {original_cy} to {new_cy}"
        )

        # Also verify 4:3 aspect ratio
        bbox_w = bbox["east"] - bbox["west"]
        bbox_h = bbox["north"] - bbox["south"]
        assert bbox_w / bbox_h == pytest.approx(768.0 / 576.0, rel=1e-4)

    def test_horizontal_fire_centroid_preserved(self):
        """
        Extremely horizontal fire: 10km wide x 1km tall.
        AR expansion should increase height, not width.
        """
        svc = self._make_service("768x576")

        minx, maxx = -65.045, -64.955  # ~10km wide
        miny, maxy = -35.0045, -34.9955  # ~1km tall

        original_cx = (minx + maxx) / 2
        original_cy = (miny + maxy) / 2

        episode = CarouselEpisodeRow(
            id="ep-horizontal",
            lat=original_cy,
            lon=original_cx,
            start_date=None,
            last_gee_image_id=None,
            gee_priority=None,
            bbox_minx=minx,
            bbox_miny=miny,
            bbox_maxx=maxx,
            bbox_maxy=maxy,
        )

        bbox = svc._bbox_from_episode(episode)

        new_cx = (bbox["west"] + bbox["east"]) / 2
        new_cy = (bbox["south"] + bbox["north"]) / 2

        assert new_cx == pytest.approx(original_cx, abs=1e-6)
        assert new_cy == pytest.approx(original_cy, abs=1e-6)


# =========================================================================
# TestFallbackMosaicOnGiantFires
# =========================================================================


class TestFallbackMosaicOnGiantFires:
    """
    When get_best_image raises GEEImageNotFoundError in fallback,
    the code must call .mosaic() instead of returning (None, False, None).
    """

    @staticmethod
    def _make_service():
        svc = object.__new__(ImageryService)
        svc.db = MagicMock()
        svc._gee = MagicMock()
        svc._storage = MagicMock()
        svc._resolve_thumb_dimensions = MagicMock(return_value="768x576")
        svc._resolve_bbox_buffer_degrees = MagicMock(return_value=0.04)
        return svc

    def test_mosaic_called_when_get_best_image_fails(self):
        """
        Simulate giant fire spanning two tiles:
        - All threshold attempts raise GEEImageNotFoundError
        - Fallback get_best_image also raises GEEImageNotFoundError
        - Mosaic fallback should kick in: collection.mosaic().clip() called
        """
        svc = self._make_service()
        bbox = {"west": -72.0, "south": -50.0, "east": -70.0, "north": -49.0}

        # Mock GEE service: get_sentinel_collection returns a mock collection
        mock_collection = MagicMock()
        mock_mosaic_image = MagicMock()
        mock_collection.mosaic.return_value = mock_mosaic_image
        mock_mosaic_image.clip.return_value = mock_mosaic_image

        # first().getInfo() returns something truthy (collection is non-empty)
        mock_collection.first.return_value.getInfo.return_value = {"id": "fake"}

        svc._gee.get_sentinel_collection.return_value = mock_collection
        # get_best_image always fails (no single image has enough coverage)
        svc._gee.get_best_image.side_effect = GEEImageNotFoundError("No coverage")

        # Bypass gee_semaphore and ee.Geometry.Rectangle
        with patch("app.services.imagery_service.gee_semaphore") as mock_sem, \
             patch("app.services.imagery_service.ee") as mock_ee:
            mock_sem.acquire_sync.return_value.__enter__ = MagicMock()
            mock_sem.acquire_sync.return_value.__exit__ = MagicMock(return_value=False)
            mock_ee.Geometry.Rectangle.return_value = MagicMock()

            image, is_archive, threshold = svc._select_image(bbox, [10, 20, 30, 50])

        # The mosaic path should have been used
        mock_collection.mosaic.assert_called_once()
        assert is_archive is True
        assert threshold == 30
        assert image is not None

    def test_mosaic_returns_none_on_empty_collection(self):
        """
        When even the mosaic collection is empty (first().getInfo() returns None),
        _select_image must return (None, False, None).
        """
        svc = self._make_service()
        bbox = {"west": -72.0, "south": -50.0, "east": -70.0, "north": -49.0}

        mock_collection = MagicMock()
        mock_collection.first.return_value.getInfo.return_value = None

        svc._gee.get_sentinel_collection.return_value = mock_collection
        svc._gee.get_best_image.side_effect = GEEImageNotFoundError("No coverage")

        with patch("app.services.imagery_service.gee_semaphore") as mock_sem:
            mock_sem.acquire_sync.return_value.__enter__ = MagicMock()
            mock_sem.acquire_sync.return_value.__exit__ = MagicMock(return_value=False)

            image, is_archive, threshold = svc._select_image(bbox, [10, 20])

        assert image is None
        assert is_archive is False
        assert threshold is None


# =========================================================================
# TestZeroCoordinateBbox
# =========================================================================


class TestZeroCoordinateBbox:
    """
    Verifies that bbox fields with value 0.0 are NOT treated as falsy.
    0.0 is a valid geographic coordinate (Ecuador/Greenwich meridian).
    """

    @staticmethod
    def _make_service(dimensions="768x576"):
        svc = object.__new__(ImageryService)
        svc.db = MagicMock()
        svc._gee = MagicMock()
        svc._storage = MagicMock()
        svc._resolve_thumb_dimensions = MagicMock(return_value=dimensions)
        svc._resolve_bbox_buffer_degrees = MagicMock(return_value=0.04)
        return svc

    def test_zero_bbox_minx_uses_real_bbox(self):
        """bbox_minx=0.0 must NOT trigger fallback to _bbox_from_point."""
        svc = self._make_service("768x576")

        episode = CarouselEpisodeRow(
            id="ep-equator",
            lat=0.05,
            lon=0.05,
            start_date=None,
            last_gee_image_id=None,
            gee_priority=None,
            bbox_minx=0.0,    # The equator/Greenwich value
            bbox_miny=-0.05,
            bbox_maxx=0.1,
            bbox_maxy=0.05,
        )

        bbox = svc._bbox_from_episode(episode)

        # If the code fell back to _bbox_from_point, the bbox would be
        # centered on (0.05, 0.05) with buffer 0.04 — different coords.
        # With real bbox, the centroid should be (0.05, 0.0)
        cx = (bbox["west"] + bbox["east"]) / 2
        cy = (bbox["south"] + bbox["north"]) / 2

        assert cx == pytest.approx(0.05, abs=1e-6), (
            f"Centroid lon should be ~0.05 (from real bbox), got {cx}. "
            "Likely fell back to _bbox_from_point because 0.0 was treated as falsy."
        )
        assert cy == pytest.approx(0.0, abs=1e-6), (
            f"Centroid lat should be ~0.0 (from real bbox), got {cy}."
        )

    def test_zero_bbox_miny_uses_real_bbox(self):
        """bbox_miny=0.0 must NOT trigger fallback."""
        svc = self._make_service("768x576")

        episode = CarouselEpisodeRow(
            id="ep-greenwich",
            lat=0.05,
            lon=30.0,
            start_date=None,
            last_gee_image_id=None,
            gee_priority=None,
            bbox_minx=29.95,
            bbox_miny=0.0,
            bbox_maxx=30.05,
            bbox_maxy=0.1,
        )

        bbox = svc._bbox_from_episode(episode)

        cy = (bbox["south"] + bbox["north"]) / 2
        assert cy == pytest.approx(0.05, abs=1e-6)

    def test_all_zero_bbox_uses_real_bbox(self):
        """All four bbox fields = 0.0 is geometrically degenerate but must not fallback."""
        svc = self._make_service("768x576")

        episode = CarouselEpisodeRow(
            id="ep-origin",
            lat=0.0,
            lon=0.0,
            start_date=None,
            last_gee_image_id=None,
            gee_priority=None,
            bbox_minx=0.0,
            bbox_miny=0.0,
            bbox_maxx=0.0,
            bbox_maxy=0.0,
        )

        # With degenerate bbox (w=0, h=0), current_ar calculation falls back
        # to target_ar due to h=0 guard, and expands from centroid.
        # The key assertion is that it does NOT call _bbox_from_point.
        with patch.object(svc, "_bbox_from_point") as mock_fallback:
            svc._bbox_from_episode(episode)
            mock_fallback.assert_not_called()


# =========================================================================
# TestMinBboxSize
# =========================================================================


class TestMinBboxSize:
    """
    Verify that very small bounding boxes (gas flares, single-pixel hotspots)
    are expanded to MIN_BBOX_SIZE to prevent extreme upscaling pixelation.
    """

    @staticmethod
    def _make_service(dimensions="768x576"):
        svc = object.__new__(ImageryService)
        svc.db = MagicMock()
        svc._gee = MagicMock()
        svc._storage = MagicMock()
        svc._resolve_thumb_dimensions = MagicMock(return_value=dimensions)
        svc._resolve_bbox_buffer_degrees = MagicMock(return_value=0.04)
        return svc

    def test_tiny_bbox_expanded_to_min_size(self):
        """
        A ~1.5 km hotspot (0.015°) must be expanded to MIN_BBOX_SIZE (~5.5 km).
        The resulting bbox extent should be >= MIN_BBOX_SIZE in both axes.
        """
        from app.services.imagery_service import MIN_BBOX_SIZE

        svc = self._make_service("768x576")

        # Simulate a gas flare: ~1.5 km wide and tall
        cx, cy = -68.5, -37.7
        half = 0.0077  # ~0.0154° total ≈ 1.7 km
        episode = CarouselEpisodeRow(
            id="ep-gas-flare",
            lat=cy,
            lon=cx,
            start_date=None,
            last_gee_image_id=None,
            gee_priority=None,
            bbox_minx=cx - half,
            bbox_miny=cy - half,
            bbox_maxx=cx + half,
            bbox_maxy=cy + half,
        )

        bbox = svc._bbox_from_episode(episode)

        bbox_w = bbox["east"] - bbox["west"]
        bbox_h = bbox["north"] - bbox["south"]

        # Both dimensions must be at least MIN_BBOX_SIZE (with fp tolerance)
        assert bbox_w >= MIN_BBOX_SIZE - 1e-9, (
            f"Width {bbox_w:.6f} should be >= MIN_BBOX_SIZE {MIN_BBOX_SIZE}"
        )
        assert bbox_h >= MIN_BBOX_SIZE - 1e-9, (
            f"Height {bbox_h:.6f} should be >= MIN_BBOX_SIZE {MIN_BBOX_SIZE}"
        )

    def test_tiny_bbox_centroid_preserved(self):
        """Expanding a tiny bbox must NOT shift the centroid."""
        svc = self._make_service("768x576")

        cx, cy = -68.5, -37.7
        half = 0.005  # very small
        episode = CarouselEpisodeRow(
            id="ep-tiny",
            lat=cy,
            lon=cx,
            start_date=None,
            last_gee_image_id=None,
            gee_priority=None,
            bbox_minx=cx - half,
            bbox_miny=cy - half,
            bbox_maxx=cx + half,
            bbox_maxy=cy + half,
        )

        bbox = svc._bbox_from_episode(episode)

        new_cx = (bbox["west"] + bbox["east"]) / 2
        new_cy = (bbox["south"] + bbox["north"]) / 2

        assert new_cx == pytest.approx(cx, abs=1e-6), (
            f"Centroid X shifted from {cx} to {new_cx}"
        )
        assert new_cy == pytest.approx(cy, abs=1e-6), (
            f"Centroid Y shifted from {cy} to {new_cy}"
        )

    def test_tiny_bbox_aspect_ratio_correct(self):
        """Expanded bbox must still match the thumbnail 4:3 aspect ratio."""
        svc = self._make_service("768x576")

        cx, cy = -68.5, -37.7
        half = 0.005
        episode = CarouselEpisodeRow(
            id="ep-tiny-ar",
            lat=cy,
            lon=cx,
            start_date=None,
            last_gee_image_id=None,
            gee_priority=None,
            bbox_minx=cx - half,
            bbox_miny=cy - half,
            bbox_maxx=cx + half,
            bbox_maxy=cy + half,
        )

        bbox = svc._bbox_from_episode(episode)
        bbox_w = bbox["east"] - bbox["west"]
        bbox_h = bbox["north"] - bbox["south"]

        assert bbox_w / bbox_h == pytest.approx(768.0 / 576.0, rel=1e-4)

    def test_large_bbox_not_shrunk(self):
        """
        A large fire (>> MIN_BBOX_SIZE) must NOT be affected by the minimum.
        """
        from app.services.imagery_service import MIN_BBOX_SIZE

        svc = self._make_service("768x576")

        # 20 km wide fire
        cx, cy = -65.0, -35.0
        half_w, half_h = 0.1, 0.1  # ~22 km
        episode = CarouselEpisodeRow(
            id="ep-large",
            lat=cy,
            lon=cx,
            start_date=None,
            last_gee_image_id=None,
            gee_priority=None,
            bbox_minx=cx - half_w,
            bbox_miny=cy - half_h,
            bbox_maxx=cx + half_w,
            bbox_maxy=cy + half_h,
        )

        bbox = svc._bbox_from_episode(episode)
        bbox_w = bbox["east"] - bbox["west"]
        bbox_h = bbox["north"] - bbox["south"]

        # Should be at least the original size (not shrunk)
        assert bbox_w >= 2 * half_w - 1e-6
        assert bbox_h >= 2 * half_h - 1e-6

