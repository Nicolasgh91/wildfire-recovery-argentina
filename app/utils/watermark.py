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


def _format_date(value: Optional[date | datetime]) -> str:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return ""


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
    When Pillow is unavailable, returns the original bytes unchanged.

    Feature flags (environment variables):
      DISABLE_WATERMARK_ALL  - skip all watermark processing
      DISABLE_WATERMARK_LOGO - skip logo only; text watermark still applied
    """
    if not PIL_AVAILABLE:
        logger.warning("Pillow not available; skipping watermark")
        return image_bytes

    disable_all = os.environ.get("DISABLE_WATERMARK_ALL", "").lower() in {"true", "1", "yes"}
    if disable_all:
        logger.info("Watermark completely disabled via DISABLE_WATERMARK_ALL")
        return image_bytes

    disable_logo = os.environ.get("DISABLE_WATERMARK_LOGO", "").lower() in {"true", "1", "yes"}
    if disable_logo:
        logger.info("Watermark logo disabled via DISABLE_WATERMARK_LOGO")
        logo_path = None

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
                    # PNG tEXt chunks require latin-1 encoding; replace any
                    # non-representable characters rather than raising at the C level.
                    safe_value = str(value).encode("latin-1", errors="replace").decode("latin-1")
                    pnginfo.add_text(str(key), safe_value)
            except Exception as metadata_exc:
                logger.warning("Failed to create PNG metadata: %s", metadata_exc)
                pnginfo = None

        try:
            combined.save(output, format="PNG", pnginfo=pnginfo, compress_level=6)
            result = output.getvalue()

            # A genuine 768x576 satellite PNG at compress_level=6 is always >10 KB.
            # Anything smaller indicates the image data was destroyed.
            if len(result) < 10_000:
                logger.warning(
                    "Watermark result suspiciously small (%d bytes); falling back to original",
                    len(result),
                )
                return image_bytes

            # Validate PNG structure without decoding all pixels (cheaper than np.array).
            Image.open(BytesIO(result)).verify()
            logger.debug("Watermark applied successfully, size: %d bytes", len(result))
            return result

        except Exception as save_exc:
            logger.warning("Failed to save watermarked PNG, falling back: %s", save_exc)
            return image_bytes

    except Exception as exc:  # pragma: no cover - safe fallback
        logger.warning("Failed to apply watermark: %s", exc)
        return image_bytes
