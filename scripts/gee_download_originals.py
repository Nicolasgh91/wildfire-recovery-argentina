#!/usr/bin/env python3
"""
Download high-resolution imagery from GEE for one episode and generate local size variants.

Commands:
  - Basic (downloads master images at 3072x2304):
      python scripts/gee_download_originals.py --episode-id <UUID>
  - Custom master size and variants:
      python scripts/gee_download_originals.py --episode-id <UUID> --master-dim 4096x3072 --sizes 1024x768,768x576,512x384
  - Skip original GeoTIFF download:
      python scripts/gee_download_originals.py --episode-id <UUID> --no-original
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Iterable, Tuple

import requests

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - optional dependency
    load_dotenv = None

try:
    from PIL import Image
    PIL_AVAILABLE = True
except Exception:  # pragma: no cover - optional dependency
    PIL_AVAILABLE = False

from app.db.session import SessionLocal
from app.services.imagery_service import ImageryService
from app.services.gee_service import GEEImageNotFoundError


logger = logging.getLogger(__name__)

DOWNLOAD_BANDS = {
    "RGB": (["B4", "B3", "B2"], 10),
    "SWIR": (["B12", "B11", "B4"], 20),
}


def _parse_size(value: str) -> Tuple[int, int]:
    cleaned = value.lower().strip()
    if "x" not in cleaned:
        raise ValueError(f"Invalid size '{value}', expected WIDTHxHEIGHT")
    width, height = cleaned.split("x", 1)
    return int(width), int(height)


def _parse_sizes(value: str) -> Iterable[Tuple[int, int]]:
    if not value:
        return []
    sizes = []
    for item in value.split(","):
        sizes.append(_parse_size(item))
    return sizes


def _download_bytes(url: str) -> bytes:
    response = requests.get(url, timeout=180)
    response.raise_for_status()
    return response.content


def _detect_extension(payload: bytes) -> str:
    if payload.startswith(b"PK"):
        return ".zip"
    if payload.startswith(b"MM") or payload.startswith(b"II"):
        return ".tif"
    return ".bin"


def _resize_and_save(master_path: Path, sizes: Iterable[Tuple[int, int]]) -> None:
    if not sizes:
        return
    if not PIL_AVAILABLE:
        logger.warning("Pillow no esta instalado; se omiten los resize locales.")
        return

    with Image.open(master_path) as image:
        image.load()
        if image.mode not in ("RGB", "RGBA"):
            image = image.convert("RGB")
        for width, height in sizes:
            resized = image.resize((width, height), resample=Image.LANCZOS)
            out_path = master_path.with_name(
                master_path.stem.rsplit("_", 1)[0] + f"_{width}x{height}.png"
            )
            resized.save(out_path, optimize=True)


def _download_master_with_fallback(
    service: ImageryService,
    image,
    bbox,
    vis_type: str,
    dimensions: Iterable[str],
    resample: str | None,
) -> tuple[bytes, str]:
    last_error: Exception | None = None
    for dim in dimensions:
        try:
            return (
                service._gee.download_thumbnail(
                    image,
                    bbox,
                    vis_type=vis_type,
                    dimensions=dim,
                    resample=resample,
                    format="png",
                ),
                dim,
            )
        except Exception as exc:  # pragma: no cover - GEE errors vary
            last_error = exc
            if "Total request size" in str(exc):
                logger.warning("Dim %s excede el limite de GEE, probando menor...", dim)
                continue
            raise
    if last_error:
        raise last_error
    raise RuntimeError("No se pudo descargar master thumbnail.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Download GEE originals and generate local variants.")
    parser.add_argument("--episode-id", required=True, help="Fire episode UUID")
    parser.add_argument("--master-dim", default="3072x2304", help="Master size WIDTHxHEIGHT")
    parser.add_argument(
        "--fallback-dims",
        default="2560x1920,2048x1536",
        help="Fallback sizes WIDTHxHEIGHT if master exceeds GEE limits",
    )
    parser.add_argument(
        "--sizes",
        default="1024x768,768x576,512x384",
        help="Comma-separated sizes WIDTHxHEIGHT for local variants",
    )
    parser.add_argument(
        "--vis",
        default="RGB,SWIR,NBR",
        help="Comma-separated vis types to download",
    )
    parser.add_argument(
        "--resample",
        default="bicubic",
        help="Resample method for getThumbURL (nearest, bilinear, bicubic).",
    )
    parser.add_argument(
        "--output-dir",
        default="storage/experiments",
        help="Output directory",
    )
    parser.add_argument(
        "--no-original",
        action="store_true",
        help="Skip GeoTIFF original download",
    )
    args = parser.parse_args()

    if load_dotenv is not None:
        load_dotenv()

    master_dim = args.master_dim
    fallback_dims = [d.strip() for d in args.fallback_dims.split(",") if d.strip()]
    dim_candidates = [master_dim, *fallback_dims]
    size_variants = list(_parse_sizes(args.sizes))
    vis_types = [item.strip().upper() for item in args.vis.split(",") if item.strip()]
    resample = args.resample.strip().lower() if args.resample else None

    db = SessionLocal()
    try:
        service = ImageryService(db)
        service._gee.authenticate()

        episode = service._fetch_episode_by_id(args.episode_id)
        if not episode:
            raise SystemExit(f"Episodio no encontrado: {args.episode_id}")
        if episode.lat is None or episode.lon is None:
            raise SystemExit(f"Episodio sin centroides: {args.episode_id}")

        bbox = service._bbox_from_point(episode.lat, episode.lon)

        if episode.last_gee_image_id:
            image = service._gee.get_image_by_id(episode.last_gee_image_id)
        else:
            thresholds = service._resolve_cloud_thresholds()
            image, _is_archive, _used_threshold = service._select_image(bbox, thresholds)
            if image is None:
                raise SystemExit("No se pudo encontrar imagen GEE para el episodio.")

        metadata = service._gee.get_image_metadata(image)
        date_str = metadata.acquisition_date.strftime("%Y%m%d") if metadata.acquisition_date else "unknown"

        base_dir = Path(args.output_dir) / episode.id
        base_dir.mkdir(parents=True, exist_ok=True)

        for vis_type in vis_types:
            vis_key = vis_type.upper()

            if not args.no_original and vis_key in DOWNLOAD_BANDS:
                bands, scale = DOWNLOAD_BANDS[vis_key]
                try:
                    download_url = service._gee.get_download_url(
                        image,
                        bbox,
                        bands=bands,
                        scale=scale,
                        format="GEO_TIFF",
                    )
                    payload = _download_bytes(download_url)
                    ext = _detect_extension(payload)
                    original_path = base_dir / f"{vis_key.lower()}_{date_str}_original{ext}"
                    original_path.write_bytes(payload)
                    logger.info("Original descargado: %s", original_path)
                except GEEImageNotFoundError as exc:
                    logger.warning("No se pudo descargar original %s: %s", vis_key, exc)

            master_bytes, used_dim = _download_master_with_fallback(
                service,
                image,
                bbox,
                vis_key,
                dim_candidates,
                resample,
            )
            master_path = base_dir / f"{vis_key.lower()}_{date_str}_{used_dim}.png"
            master_path.write_bytes(master_bytes)
            logger.info("Master guardado: %s", master_path)

            _resize_and_save(master_path, size_variants)

        logger.info("Listo. Carpeta de salida: %s", base_dir)
    finally:
        db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
