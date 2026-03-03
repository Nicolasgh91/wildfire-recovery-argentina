from __future__ import annotations

import logging
import os
from datetime import date, datetime
from io import BytesIO
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)

try:
    from PIL import Image, ImageDraw, ImageFont, PngImagePlugin
    PIL_AVAILABLE = True
except Exception:  # pragma: no cover - optional dependency
    Image = None  # type: ignore
    ImageDraw = None  # type: ignore
    ImageFont = None  # type: ignore
    PngImagePlugin = None  # type: ignore
    PIL_AVAILABLE = False

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False


def _format_date(value: Optional[date | datetime]) -> str:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return ""


def _fix_corrupted_png(png_bytes: bytes) -> bytes:
    """
    Fix corrupted PNG by reconstructing from pixel data.
    
    This handles the case where PNG metadata corruption prevents
    normal PIL operations like save() or numpy conversion.
    """
    try:
        # Try to load the image
        img = Image.open(BytesIO(png_bytes))
        
        # Test if it's corrupted by attempting save
        test_output = BytesIO()
        img.save(test_output, format='PNG')
        return png_bytes  # Not corrupted, return original
        
    except Exception:
        # Image is corrupted, reconstruct it
        logger.info("Reconstructing corrupted PNG from pixel data")
        
        try:
            # Reload the image (it might open but fail on save)
            img = Image.open(BytesIO(png_bytes))
            width, height = img.size
            
            if not NUMPY_AVAILABLE:
                logger.warning("NumPy not available, cannot fix corrupted PNG")
                return png_bytes
            
            # Create new array and copy pixels manually
            if img.mode == 'RGBA':
                arr = np.zeros((height, width, 4), dtype=np.uint8)
                
                # Copy pixels manually
                for y in range(height):
                    for x in range(width):
                        try:
                            pixel = img.getpixel((x, y))
                            arr[y, x] = pixel
                        except Exception:
                            # Use transparent pixel if getpixel fails
                            arr[y, x] = [0, 0, 0, 0]
            else:
                # Convert to RGBA first
                img_rgba = img.convert('RGBA')
                arr = np.zeros((height, width, 4), dtype=np.uint8)
                
                for y in range(height):
                    for x in range(width):
                        try:
                            pixel = img_rgba.getpixel((x, y))
                            arr[y, x] = pixel
                        except Exception:
                            arr[y, x] = [0, 0, 0, 0]
            
            # Create new image from array
            fixed_img = Image.fromarray(arr, 'RGBA')
            
            # Save without metadata
            output = BytesIO()
            fixed_img.save(output, format='PNG', compress_level=6)
            
            logger.info("Successfully reconstructed corrupted PNG")
            return output.getvalue()
            
        except Exception as e:
            logger.warning("Failed to reconstruct corrupted PNG: %s", e)
            return png_bytes


def apply_watermark(
    image_bytes: bytes,
    *,
    acquisition_date: Optional[date | datetime] = None,
    label: Optional[str] = None,
    logo_path: Optional[Path] = None,
    metadata: Optional[Dict[str, str]] = None,
) -> bytes:
    """
    Apply a watermark with logo (bottom-right) and date text (bottom-left).
    When Pillow is unavailable, returns the original bytes.
    
    Feature flags:
    - DISABLE_WATERMARK_LOGO: Skip logo processing if set to 'true', '1', or 'yes'
    - DISABLE_WATERMARK_ALL: Skip all watermark processing if set to 'true', '1', or 'yes'
    """
    if not PIL_AVAILABLE:
        logger.warning("Pillow not available; skipping watermark")
        return image_bytes

    # Check feature flags
    disable_all = os.environ.get("DISABLE_WATERMARK_ALL", "").lower() in {"true", "1", "yes"}
    if disable_all:
        logger.info("Watermark completely disabled via DISABLE_WATERMARK_ALL")
        return image_bytes
        
    disable_logo = os.environ.get("DISABLE_WATERMARK_LOGO", "").lower() in {"true", "1", "yes"}
    if disable_logo:
        logger.info("Watermark logo disabled via DISABLE_WATERMARK_LOGO")
        logo_path = None

    # Fix corrupted input if needed
    try:
        test_img = Image.open(BytesIO(image_bytes))
        test_output = BytesIO()
        test_img.save(test_output, format='PNG')
    except Exception:
        logger.info("Input PNG appears corrupted, attempting reconstruction")
        image_bytes = _fix_corrupted_png(image_bytes)

    try:
        base = Image.open(BytesIO(image_bytes)).convert("RGBA")
        overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        text = _format_date(acquisition_date)
        if label:
            text = f"{text} | {label}" if text else label

        font = ImageFont.load_default()
        if text:
            text_padding = 6
            text_bbox = draw.textbbox((0, 0), text, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            x = text_padding
            y = base.height - text_height - text_padding
            draw.rectangle(
                [(x - 4, y - 2), (x + text_width + 4, y + text_height + 2)],
                fill=(0, 0, 0, 110),
            )
            draw.text((x, y), text, fill=(255, 255, 255, 210), font=font)

        if logo_path and logo_path.exists():
            logo = Image.open(logo_path).convert("RGBA")
            max_width = int(base.width * 0.2)
            if logo.width > max_width:
                ratio = max_width / float(logo.width)
                new_size = (max_width, max(1, int(logo.height * ratio)))
                logo = logo.resize(new_size)
            logo_x = base.width - logo.width - 8
            logo_y = base.height - logo.height - 8
            overlay.paste(logo, (logo_x, logo_y), logo)

        combined = Image.alpha_composite(base, overlay)

        output = BytesIO()
        pnginfo = None
        if metadata and PngImagePlugin is not None:
            try:
                pnginfo = PngImagePlugin.PngInfo()
                for key, value in metadata.items():
                    if value is None:
                        continue
                    pnginfo.add_text(str(key), str(value))
            except Exception as metadata_exc:
                logger.warning("Failed to create PNG metadata: %s", metadata_exc)
                pnginfo = None

        # Save without redundant convert() call - combined is already RGBA
        try:
            combined.save(output, format="PNG", pnginfo=pnginfo, compress_level=6)
            result = output.getvalue()
            
            # Validate the result before returning
            try:
                test_img = Image.open(BytesIO(result))
                # Quick numpy test to catch corruption early
                import numpy as np
                arr = np.array(test_img)
                logger.debug("Watermark applied successfully, size: %d bytes", len(result))
                return result
            except Exception as validation_exc:
                logger.warning("Watermark produced corrupted PNG, falling back: %s", validation_exc)
                return image_bytes
                
        except Exception as save_exc:
            logger.warning("Failed to save watermarked PNG, falling back: %s", save_exc)
            return image_bytes
    except Exception as exc:  # pragma: no cover - safe fallback
        logger.warning("Failed to apply watermark: %s", exc)
        return image_bytes
