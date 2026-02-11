"""
=============================================================================
FORESTGUARD - IMAGERY SERVICE (UC-F08)
=============================================================================

Service for daily carousel thumbnails and satellite imagery generation.

Features:
    - Daily batch processing of active fire episodes
    - Sentinel-2 image selection with cloud cover thresholds
    - Multiple visualization types (RGB, SWIR, NBR)
    - Watermarking with acquisition date and metadata
    - Storage integration for thumbnail uploads

Use Case:
    UC-F08: Daily Carousel Thumbnails
    
    Active fire episodes are processed daily to generate fresh
    satellite imagery for the homepage carousel, showing recent
    fire activity with high-quality visualizations.

Processing Pipeline:
    1. Fetch priority episodes (active + gee_candidate)
    2. For each episode: select best recent Sentinel-2 image
    3. Generate thumbnails in multiple visualization modes
    4. Apply watermark with branding and metadata
    5. Upload to storage and update episode record

Image Selection Strategy:
    - Progressive cloud thresholds: 10% → 20% → 30% → 50%
    - Fallback to 30-day archive if no recent clear imagery
    - Quality scores: excellent/good/fair/poor/unusable

Dependencies:
    - app.services.gee_service: Google Earth Engine access
    - app.services.storage_service: R2/GCS/local storage
    - app.utils.watermark: Image watermarking utility

Author: ForestGuard Team
Version: 2.0.0
Last Updated: 2026-02-08
=============================================================================
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Union
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.episode import FireEpisode
from app.models.evidence import SatelliteImage
from app.models.fire import FireEvent
from app.services.gee_service import (
    GEEAuthenticationError,
    GEEImageNotFoundError,
    GEERateLimitError,
    GEEService,
)
from app.services.storage_service import StorageService
from app.utils.watermark import apply_watermark

logger = logging.getLogger(__name__)


DEFAULT_BATCH_SIZE = 15
DEFAULT_CLOUD_THRESHOLDS = [10, 20, 30, 50]

THUMB_DIMENSIONS: Union[int, str] = "768x576"
CAROUSEL_IMAGE_TYPE = "carousel"
DEFAULT_CAROUSEL_BBOX_BUFFER_DEGREES = 0.04
DEFAULT_CAROUSEL_GEE_RESAMPLE = "bicubic"
DEFAULT_WATERMARK_LOGO_RELATIVE_PATH = "app/assets/branding/watermark-logo.png"

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_WATERMARK_LOGO_PATH = REPO_ROOT / DEFAULT_WATERMARK_LOGO_RELATIVE_PATH

VISUALS = {
    "SWIR": {
        "bands": ["B12", "B11", "B4"],
        "min": [0, 0, 0],
        "max": [5000, 5000, 5000],
        "gamma": [1.0, 1.0, 1.0],
        "spatial_resolution": 20,
    },
    "RGB": {
        "bands": ["B4", "B3", "B2"],
        "min": 0,
        "max": 3000,
        "gamma": 1.2,
        "spatial_resolution": 10,
    },
    "NBR": {
        "bands": ["B8", "B12"],
        "min": -0.5,
        "max": 0.5,
        "palette": ["#00FF00", "#FFFF00", "#FF7F00", "#FF0000", "#000000"],
        "formula": "(B8-B12)/(B8+B12)",
        "spatial_resolution": 20,
    },
}


@dataclass(frozen=True)
class CarouselEpisodeRow:
    """Episode row used to build carousel thumbnails."""
    id: str
    lat: Optional[float]
    lon: Optional[float]
    start_date: Optional[datetime]
    last_gee_image_id: Optional[str]
    gee_priority: Optional[int]


@dataclass(frozen=True)
class CarouselFireRow:
    """Fire row used to rank carousel candidates."""
    id: str
    lat: Optional[float]
    lon: Optional[float]
    start_date: Optional[datetime]
    last_gee_image_id: Optional[str]
    max_frp: Optional[float]
    estimated_area_hectares: Optional[float]
    h3_index: Optional[str]
    priority_score: Optional[float]


@dataclass(frozen=True)
class RepresentativeEventRow:
    """Representative fire event selection row."""
    id: str
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    status: Optional[str]


class ImageryService:
    """
    UC-F08: Daily carousel thumbnails for active episodes.
    """

    def __init__(
        self,
        db: Session,
        gee_service: Optional[GEEService] = None,
        storage_service: Optional[StorageService] = None,
    ):
        self.db = db
        self._gee = gee_service or GEEService()
        self._storage = storage_service or StorageService()

    def _get_system_param(self, key: str) -> Optional[object]:
        try:
            row = (
                self.db.execute(
                    text(
                        "SELECT param_value FROM system_parameters WHERE param_key = :key"
                    ),
                    {"key": key},
                )
                .mappings()
                .first()
            )
        except SQLAlchemyError as exc:
            logger.warning("system_parameters lookup failed for %s: %s", key, exc)
            self.db.rollback()
            return None
        if not row:
            return None
        return row.get("param_value")

    def _resolve_batch_size(self, override: Optional[int] = None) -> int:
        if override:
            return int(override)
        value = self._get_system_param("carousel_batch_size")
        if isinstance(value, dict) and "value" in value:
            try:
                return int(value["value"])
            except (TypeError, ValueError):
                return DEFAULT_BATCH_SIZE
        return DEFAULT_BATCH_SIZE

    def _resolve_cloud_thresholds(self) -> List[int]:
        value = self._get_system_param("cloud_coverage_thresholds")
        if not isinstance(value, dict):
            return DEFAULT_CLOUD_THRESHOLDS

        thresholds: List[int] = []
        initial = value.get("initial")
        if isinstance(initial, (int, float)):
            thresholds.append(int(initial))

        increments = value.get("increments") or []
        if isinstance(increments, list):
            for item in increments:
                if isinstance(item, (int, float)):
                    thresholds.append(int(item))

        max_value = value.get("max")
        if isinstance(max_value, (int, float)):
            max_value = int(max_value)
            if max_value not in thresholds:
                thresholds.append(max_value)

        if not thresholds:
            return DEFAULT_CLOUD_THRESHOLDS

        # Preserve order, remove duplicates
        seen = set()
        ordered: List[int] = []
        for item in thresholds:
            if item in seen:
                continue
            seen.add(item)
            ordered.append(item)
        return ordered

    def _quality_score(self, cloud_cover: float) -> str:
        if cloud_cover <= 10:
            return "excellent"
        if cloud_cover <= 20:
            return "good"
        if cloud_cover <= 30:
            return "fair"
        if cloud_cover <= 50:
            return "poor"
        return "unusable"

    def _resolve_bbox_buffer_degrees(self) -> float:
        raw = os.environ.get("CAROUSEL_BBOX_BUFFER_DEG")
        if not raw:
            return DEFAULT_CAROUSEL_BBOX_BUFFER_DEGREES
        try:
            return float(raw)
        except ValueError:
            logger.warning(
                "Invalid CAROUSEL_BBOX_BUFFER_DEG=%r, using default=%s",
                raw,
                DEFAULT_CAROUSEL_BBOX_BUFFER_DEGREES,
            )
            return DEFAULT_CAROUSEL_BBOX_BUFFER_DEGREES

    def _resolve_thumb_dimensions(self) -> Union[int, str]:
        raw = os.environ.get("CAROUSEL_THUMB_DIMENSIONS")
        if not raw:
            return THUMB_DIMENSIONS
        raw = raw.strip()
        if not raw:
            return THUMB_DIMENSIONS
        if raw.isdigit():
            return int(raw)
        return raw

    def _resolve_gee_resample(self) -> Optional[str]:
        raw = (
            os.environ.get("CAROUSEL_GEE_RESAMPLE", DEFAULT_CAROUSEL_GEE_RESAMPLE)
            .strip()
            .lower()
        )
        if raw in {"", "none", "off", "false", "0"}:
            return None
        if raw not in {"nearest", "bilinear", "bicubic"}:
            logger.warning("Invalid CAROUSEL_GEE_RESAMPLE=%r, disabling resample", raw)
            return None
        return raw

    def _resolve_watermark_logo_path(self) -> Optional[Path]:
        """
        Resolve the logo used by the watermark overlay.

        Priority:
        1) WATERMARK_LOGO_PATH (env var). Relative paths are resolved against repo root.
        2) Default repo path: app/assets/branding/watermark-logo.png
        """
        raw = (os.environ.get("WATERMARK_LOGO_PATH") or "").strip()
        if raw:
            candidate = Path(raw)
            if not candidate.is_absolute():
                candidate = REPO_ROOT / candidate
            if candidate.exists():
                return candidate
            logger.warning("WATERMARK_LOGO_PATH points to missing file: %s", candidate)
            return None

        if DEFAULT_WATERMARK_LOGO_PATH.exists():
            return DEFAULT_WATERMARK_LOGO_PATH

        logger.warning(
            "Default watermark logo not found: %s", DEFAULT_WATERMARK_LOGO_PATH
        )
        return None

    def _bbox_from_point(
        self, lat: float, lon: float, buffer_degrees: Optional[float] = None
    ) -> Dict[str, float]:
        if buffer_degrees is None:
            buffer_degrees = self._resolve_bbox_buffer_degrees()
        return {
            "west": lon - buffer_degrees,
            "south": lat - buffer_degrees,
            "east": lon + buffer_degrees,
            "north": lat + buffer_degrees,
        }

    def _fetch_priority_episodes(self, limit: int) -> List[CarouselEpisodeRow]:
        query = text(
            """
            SELECT id,
                   centroid_lat AS lat,
                   centroid_lon AS lon,
                   start_date,
                   last_gee_image_id,
                   gee_priority
              FROM fire_episodes
             WHERE status IN ('active', 'monitoring')
               AND gee_candidate = true
             ORDER BY gee_priority DESC NULLS LAST, start_date DESC NULLS LAST
             LIMIT :limit
            """
        )
        rows = self.db.execute(query, {"limit": limit}).mappings().all()

        results: List[CarouselEpisodeRow] = []
        for row in rows:
            results.append(
                CarouselEpisodeRow(
                    id=str(row["id"]),
                    lat=float(row["lat"]) if row.get("lat") is not None else None,
                    lon=float(row["lon"]) if row.get("lon") is not None else None,
                    start_date=row.get("start_date"),
                    last_gee_image_id=row.get("last_gee_image_id"),
                    gee_priority=int(row["gee_priority"])
                    if row.get("gee_priority") is not None
                    else None,
                )
            )
        return results

    def _fetch_priority_fires(
        self, limit: int, weights: Optional[dict] = None
    ) -> List[CarouselEpisodeRow]:
        del weights
        return self._fetch_priority_episodes(limit)

    def _fetch_episode_by_id(self, episode_id: str) -> Optional[CarouselEpisodeRow]:
        query = text(
            """
            SELECT id,
                   centroid_lat AS lat,
                   centroid_lon AS lon,
                   start_date,
                   last_gee_image_id,
                   gee_priority
              FROM fire_episodes
             WHERE id = :episode_id
            """
        )
        row = self.db.execute(query, {"episode_id": str(episode_id)}).mappings().first()
        if not row:
            return None
        return CarouselEpisodeRow(
            id=str(row["id"]),
            lat=float(row["lat"]) if row.get("lat") is not None else None,
            lon=float(row["lon"]) if row.get("lon") is not None else None,
            start_date=row.get("start_date"),
            last_gee_image_id=row.get("last_gee_image_id"),
            gee_priority=int(row["gee_priority"])
            if row.get("gee_priority") is not None
            else None,
        )

    def _fetch_representative_event(
        self, episode_id: str
    ) -> Optional[RepresentativeEventRow]:
        query = text(
            """
            SELECT fe.id,
                   fe.start_date,
                   fe.end_date,
                   fe.status
              FROM fire_events fe
              JOIN fire_episode_events fee ON fee.event_id = fe.id
             WHERE fee.episode_id = :episode_id
             ORDER BY CASE WHEN fe.status IN ('active', 'monitoring') THEN 0 ELSE 1 END,
                      fe.end_date DESC NULLS LAST,
                      fe.start_date DESC NULLS LAST
             LIMIT 1
            """
        )
        row = self.db.execute(query, {"episode_id": str(episode_id)}).mappings().first()
        if not row:
            return None
        return RepresentativeEventRow(
            id=str(row["id"]),
            start_date=row.get("start_date"),
            end_date=row.get("end_date"),
            status=row.get("status"),
        )

    def _resolve_representative_event(
        self, episode_id: str
    ) -> tuple[Optional[RepresentativeEventRow], bool]:
        representative = self._fetch_representative_event(episode_id)
        if representative:
            return representative, False

        event_key = self._normalize_fire_id(episode_id)
        event = self.db.query(FireEvent).filter(FireEvent.id == event_key).first()
        if not event:
            return None, False

        return (
            RepresentativeEventRow(
                id=str(event.id),
                start_date=event.start_date,
                end_date=event.end_date,
                status=event.status,
            ),
            True,
        )

    def _first_image(self, collection) -> Any:
        try:
            image = collection.first()
            info = image.getInfo()
            if not info:
                raise GEEImageNotFoundError("No image in collection")
            return image
        except Exception as exc:
            raise GEEImageNotFoundError("No image found in collection") from exc

    def _select_image(
        self, bbox: Dict[str, float], thresholds: Iterable[int]
    ) -> tuple[Any | None, bool, Optional[int]]:
        today = date.today()
        start = today - timedelta(days=7)

        for threshold in thresholds:
            try:
                collection = self._gee.get_sentinel_collection(
                    bbox=bbox,
                    start_date=start,
                    end_date=today,
                    max_cloud_cover=float(threshold),
                )
                image = self._gee.get_best_image(collection)
                return image, False, int(threshold)
            except GEEImageNotFoundError:
                continue

        # Fallback: oldest clear image in last 30 days
        try:
            fallback_collection = self._gee.get_sentinel_collection(
                bbox=bbox,
                start_date=today - timedelta(days=30),
                end_date=today,
                max_cloud_cover=30,
            )
            oldest = fallback_collection.sort("system:time_start")
            image = self._first_image(oldest)
            return image, True, 30
        except GEEImageNotFoundError:
            return None, False, None

    def _build_metadata(self, **kwargs: Any) -> Dict[str, str]:
        metadata: Dict[str, str] = {}
        for key, value in kwargs.items():
            if value is None:
                continue
            if isinstance(value, (dict, list)):
                metadata[key] = json.dumps(value)
            else:
                metadata[key] = str(value)
        return metadata

    @staticmethod
    def _normalize_fire_id(fire_id: str) -> UUID | str:
        if isinstance(fire_id, UUID):
            return fire_id
        try:
            return UUID(str(fire_id))
        except (TypeError, ValueError):
            return fire_id

    def _upload_thumbnail(
        self,
        episode_id: str,
        vis_type: str,
        acquisition_date: Optional[date],
        image_bytes: bytes,
        metadata: Dict[str, str],
    ):
        date_str = (
            acquisition_date.strftime("%Y%m%d") if acquisition_date else "unknown"
        )
        key = f"carousel/{episode_id}/{vis_type.lower()}_{date_str}.png"
        return self._storage.upload_bytes(
            data=image_bytes,
            key=key,
            bucket=os.environ.get("STORAGE_BUCKET_IMAGES", "forestguard-images"),
            content_type="image/png",
            metadata=metadata,
        )

    def _download_thumbnail(
        self,
        image: Any,
        bbox: Dict[str, float],
        vis_type: str,
        dimensions: Union[int, str],
        resample: Optional[str],
    ) -> bytes:
        kwargs = {
            "vis_type": vis_type,
            "dimensions": dimensions,
            "format": "png",
        }
        if resample is not None:
            kwargs["resample"] = resample
        try:
            return self._gee.download_thumbnail(image, bbox, **kwargs)
        except TypeError as exc:
            if "resample" in kwargs and "resample" in str(exc):
                kwargs.pop("resample", None)
                return self._gee.download_thumbnail(image, bbox, **kwargs)
            raise

    def _delete_existing_carousel_images(self, event_id: str) -> None:
        event_key = self._normalize_fire_id(event_id)
        self.db.query(SatelliteImage).filter(
            SatelliteImage.fire_event_id == event_key,
            SatelliteImage.image_type == CAROUSEL_IMAGE_TYPE,
        ).delete(synchronize_session=False)

    def _update_episode(
        self, episode_id: str, image_id: str, slides: List[Dict[str, Any]]
    ) -> None:
        episode = (
            self.db.query(FireEpisode).filter(FireEpisode.id == episode_id).first()
        )
        if not episode:
            return
        episode.last_gee_image_id = image_id
        episode.last_update_sat = datetime.now(timezone.utc)
        episode.slides_data = slides

    def _update_fire_event(
        self, fire_event_id: str, image_id: str, slides: List[Dict[str, Any]]
    ) -> None:
        event_key = self._normalize_fire_id(fire_event_id)
        event = self.db.query(FireEvent).filter(FireEvent.id == event_key).first()
        if not event:
            return
        event.last_gee_image_id = image_id
        event.last_update_sat = datetime.now(timezone.utc)
        event.slides_data = slides

    def _process_episode(
        self,
        episode: CarouselEpisodeRow,
        thresholds: List[int],
        force_refresh: bool,
    ) -> Dict[str, Any]:
        if episode.lat is None or episode.lon is None:
            return {"status": "skipped", "reason": "missing_centroid"}

        representative, is_fire_event = self._resolve_representative_event(episode.id)
        if not representative:
            return {"status": "skipped", "reason": "missing_event"}

        bbox = self._bbox_from_point(episode.lat, episode.lon)
        image, is_archive, used_threshold = self._select_image(bbox, thresholds)
        if image is None:
            return {"status": "skipped", "reason": "no_image"}

        metadata = self._gee.get_image_metadata(image)
        if not metadata.image_id:
            return {"status": "skipped", "reason": "missing_image_id"}

        if not force_refresh and episode.last_gee_image_id == metadata.image_id:
            return {
                "status": "skipped",
                "reason": "no_change",
                "image_id": metadata.image_id,
            }

        self._delete_existing_carousel_images(representative.id)

        slides: List[Dict[str, Any]] = []
        generated_at = datetime.now(timezone.utc).isoformat()
        dimensions = self._resolve_thumb_dimensions()
        resample = self._resolve_gee_resample()
        watermark_logo = self._resolve_watermark_logo_path()
        for vis_type, vis_params in VISUALS.items():
            raw_bytes = self._download_thumbnail(
                image,
                bbox,
                vis_type=vis_type,
                dimensions=dimensions,
                resample=resample,
            )
            watermark_label = "Archivo" if is_archive else None
            watermark_meta = self._build_metadata(
                gee_system_index=metadata.image_id,
                centroid=f"{episode.lat},{episode.lon}",
                bbox=bbox,
                vis_type=vis_type,
                cloud_cover_pct=metadata.cloud_cover_percent,
                acquisition_date=metadata.acquisition_date,
                threshold=used_threshold,
            )
            processed_bytes = apply_watermark(
                raw_bytes,
                acquisition_date=metadata.acquisition_date,
                label=watermark_label,
                logo_path=watermark_logo,
                metadata=watermark_meta,
            )

            upload_result = self._upload_thumbnail(
                episode.id,
                vis_type,
                metadata.acquisition_date,
                processed_bytes,
                watermark_meta,
            )

            quality = self._quality_score(float(metadata.cloud_cover_percent))
            days_after_fire = None
            start_date = representative.start_date or episode.start_date
            if start_date and metadata.acquisition_date:
                days_after_fire = (metadata.acquisition_date - start_date.date()).days

            satellite_image = SatelliteImage(
                fire_event_id=self._normalize_fire_id(representative.id),
                satellite=metadata.satellite,
                tile_id=metadata.tile_id,
                product_id=metadata.image_id,
                acquisition_date=metadata.acquisition_date or date.today(),
                image_type=CAROUSEL_IMAGE_TYPE,
                days_after_fire=days_after_fire,
                cloud_cover_pct=float(metadata.cloud_cover_percent),
                quality_score=quality,
                usable_for_analysis=quality != "unusable",
                r2_bucket=os.environ.get("STORAGE_BUCKET_IMAGES", "forestguard-images"),
                r2_key=upload_result.key,
                r2_url=upload_result.url,
                thumbnail_url=upload_result.url,
                file_size_mb=round(upload_result.size_bytes / (1024 * 1024), 4),
                bands_included=vis_params.get("bands"),
                processing_level=metadata.processing_level
                if hasattr(metadata, "processing_level")
                else "L2A",
                spatial_resolution_meters=vis_params.get("spatial_resolution", 10),
                gee_system_index=metadata.image_id,
                visualization_params=vis_params,
                is_reproducible=True,
            )
            self.db.add(satellite_image)
            self.db.flush()

            slides.append(
                {
                    "type": vis_type.lower(),
                    "thumbnail_url": upload_result.url,
                    "satellite_image_id": str(satellite_image.id),
                    "generated_at": generated_at,
                }
            )

        self._update_episode(episode.id, metadata.image_id, slides)
        if is_fire_event:
            self._update_fire_event(representative.id, metadata.image_id, slides)
        self.db.commit()

        return {
            "status": "updated",
            "image_id": metadata.image_id,
            "slides_count": len(slides),
        }

    def run_carousel(
        self, max_fires: Optional[int] = None, force_refresh: bool = False
    ) -> Dict[str, Any]:
        self._gee.authenticate()

        batch_size = self._resolve_batch_size(max_fires)
        thresholds = self._resolve_cloud_thresholds()
        episodes = self._fetch_priority_fires(batch_size, weights=None)
        if not episodes:
            return {"processed": 0, "updated": 0, "skipped": 0, "errors": []}

        updated = 0
        skipped = 0
        errors: List[Dict[str, Any]] = []

        for episode in episodes:
            try:
                result = self._process_episode(episode, thresholds, force_refresh)
                if result.get("status") == "updated":
                    updated += 1
                else:
                    skipped += 1
            except (GEEAuthenticationError, GEERateLimitError) as exc:
                logger.exception("GEE error for episode %s: %s", episode.id, exc)
                self.db.rollback()
                raise
            except Exception as exc:
                logger.exception(
                    "Carousel update failed for episode %s: %s", episode.id, exc
                )
                self.db.rollback()
                errors.append({"episode_id": episode.id, "error": str(exc)})

        return {
            "processed": len(episodes),
            "updated": updated,
            "skipped": skipped,
            "errors": errors,
        }

    def refresh_episode(
        self, episode_id: str, force_refresh: bool = True
    ) -> Dict[str, Any]:
        self._gee.authenticate()

        thresholds = self._resolve_cloud_thresholds()
        episode = self._fetch_episode_by_id(episode_id)
        if not episode:
            return {"episode_id": str(episode_id), "status": "not_found"}

        try:
            result = self._process_episode(episode, thresholds, force_refresh)
            return {"episode_id": episode.id, **result}
        except (GEEAuthenticationError, GEERateLimitError) as exc:
            logger.exception("GEE error for episode %s: %s", episode.id, exc)
            self.db.rollback()
            raise
        except Exception as exc:
            logger.exception(
                "Manual refresh failed for episode %s: %s", episode.id, exc
            )
            self.db.rollback()
            return {"episode_id": episode.id, "status": "error", "reason": str(exc)}

    def refresh_fire(self, fire_id: str, force_refresh: bool = True) -> Dict[str, Any]:
        return self.refresh_episode(fire_id, force_refresh=force_refresh)
