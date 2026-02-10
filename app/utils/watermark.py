from __future__ import annotations

import logging
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
    When Pillow is unavailable, returns the original bytes.
    """
    if not PIL_AVAILABLE:
        logger.warning("Pillow not available; skipping watermark")
        return image_bytes

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
            pnginfo = PngImagePlugin.PngInfo()
            for key, value in metadata.items():
                if value is None:
                    continue
                pnginfo.add_text(str(key), str(value))

        combined.convert("RGBA").save(output, format="PNG", pnginfo=pnginfo)
        return output.getvalue()
    except Exception as exc:  # pragma: no cover - safe fallback
        logger.warning("Failed to apply watermark: %s", exc)
        return image_bytes
