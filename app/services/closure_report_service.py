from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional
from uuid import UUID

from sqlalchemy import bindparam, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.episode import FireEpisodeEvent
from app.models.evidence import SatelliteImage
from app.models.fire import FireEvent
from app.services.gee_service import (
    GEEAuthenticationError,
    GEEImageNotFoundError,
    GEERateLimitError,
    GEEService,
)
from app.services.storage_service import StorageService

logger = logging.getLogger(__name__)

DEFAULT_CLOUD_MAX = 40
DEFAULT_MIN_AREA_HA = 10.0
DEFAULT_MAX_RETRY_DAYS = 30

THUMB_DIMENSIONS = 256

VISUALS = {
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
    "DNBR": {
        "bands": ["B8", "B12"],
        "min": -0.5,
        "max": 0.5,
        "palette": ["#00FF00", "#FFFF00", "#FF7F00", "#FF0000", "#000000"],
        "formula": "NBR_pre - NBR_post",
        "spatial_resolution": 20,
    },
}


@dataclass(frozen=True)
class ClosureFireRow:
    """Lightweight projection of fire rows for closure report processing."""
    id: str
    lat: float
    lon: float
    start_date: datetime
    extinguished_at: datetime
    estimated_area_hectares: float


class ClosureReportService:
    """
    UC-F09: Closure report worker.
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

    def _resolve_cloud_max(self) -> int:
        value = self._get_system_param("closure_report_cloud_max")
        if value is None:
            value = self._get_system_param("closure_cloud_max")
        if isinstance(value, dict) and "value" in value:
            try:
                return int(value["value"])
            except (TypeError, ValueError):
                return DEFAULT_CLOUD_MAX
        if isinstance(value, (int, float)):
            return int(value)
        return DEFAULT_CLOUD_MAX

    def _resolve_cloud_masking(self) -> bool:
        value = self._get_system_param("closure_report_cloud_max")
        if value is None:
            value = self._get_system_param("closure_cloud_max")
        if isinstance(value, dict):
            return bool(value.get("with_cloud_masking", True))
        return True

    def _resolve_min_area(self) -> float:
        value = self._get_system_param("closure_report_min_area_ha")
        if isinstance(value, dict) and "value" in value:
            try:
                return float(value["value"])
            except (TypeError, ValueError):
                return DEFAULT_MIN_AREA_HA
        if isinstance(value, (int, float)):
            return float(value)
        return DEFAULT_MIN_AREA_HA

    def _resolve_max_retry_days(self) -> int:
        value = self._get_system_param("closure_report_max_retry_days")
        if isinstance(value, dict) and "value" in value:
            try:
                return int(value["value"])
            except (TypeError, ValueError):
                return DEFAULT_MAX_RETRY_DAYS
        if isinstance(value, (int, float)):
            return int(value)
        return DEFAULT_MAX_RETRY_DAYS

    @staticmethod
    def _bbox_from_point(
        lat: float, lon: float, buffer_degrees: float = 0.01
    ) -> Dict[str, float]:
        return {
            "west": lon - buffer_degrees,
            "south": lat - buffer_degrees,
            "east": lon + buffer_degrees,
            "north": lat + buffer_degrees,
        }

    def _fetch_candidates(
        self, limit: int, min_area: float, max_retry_days: int
    ) -> List[ClosureFireRow]:
        query = text(
            """
            SELECT fe.id,
                   ST_X(fe.centroid::geometry) AS lon,
                   ST_Y(fe.centroid::geometry) AS lat,
                   fe.start_date,
                   fe.extinguished_at,
                   fe.estimated_area_hectares
              FROM fire_events fe
             WHERE fe.status IN ('extinguished', 'contained')
               AND fe.extinguished_at IS NOT NULL
               AND fe.extinguished_at >= NOW() - (:retry_days || ' days')::interval
               AND fe.has_historic_report = false
               AND fe.estimated_area_hectares IS NOT NULL
               AND fe.estimated_area_hectares >= :min_area
               AND EXISTS (
                     SELECT 1
                       FROM fire_protected_area_intersections fpa
                      WHERE fpa.fire_event_id = fe.id
               )
             ORDER BY fe.extinguished_at DESC
             LIMIT :limit
            """
        )

        rows = (
            self.db.execute(
                query,
                {"limit": limit, "min_area": min_area, "retry_days": max_retry_days},
            )
            .mappings()
            .all()
        )

        results: List[ClosureFireRow] = []
        for row in rows:
            results.append(
                ClosureFireRow(
                    id=str(row["id"]),
                    lat=float(row["lat"]),
                    lon=float(row["lon"]),
                    start_date=row["start_date"],
                    extinguished_at=row["extinguished_at"],
                    estimated_area_hectares=float(row["estimated_area_hectares"] or 0),
                )
            )
        return results

    def _select_pre_image(
        self, bbox: Dict[str, float], start_date: date, cloud_max: int
    ):
        primary_start = start_date - timedelta(days=15)
        primary_end = start_date - timedelta(days=7)
        primary_target = start_date - timedelta(days=10)

        try:
            collection = self._gee.get_sentinel_collection(
                bbox=bbox,
                start_date=primary_start,
                end_date=primary_end,
                max_cloud_cover=cloud_max,
            )
            return self._gee.get_best_image(
                collection,
                target_date=primary_target,
                max_cloud_cover=cloud_max,
            )
        except GEEImageNotFoundError:
            fallback_start = start_date - timedelta(days=30)
            fallback_end = start_date - timedelta(days=15)
            fallback_target = start_date - timedelta(days=22)
            collection = self._gee.get_sentinel_collection(
                bbox=bbox,
                start_date=fallback_start,
                end_date=fallback_end,
                max_cloud_cover=cloud_max,
            )
            return self._gee.get_best_image(
                collection,
                target_date=fallback_target,
                max_cloud_cover=cloud_max,
            )

    def _select_post_image(
        self, bbox: Dict[str, float], extinguished_at: date, cloud_max: int
    ):
        post_start = extinguished_at
        post_end = extinguished_at + timedelta(days=14)
        post_target = extinguished_at + timedelta(days=7)
        collection = self._gee.get_sentinel_collection(
            bbox=bbox,
            start_date=post_start,
            end_date=post_end,
            max_cloud_cover=cloud_max,
        )
        return self._gee.get_best_image(
            collection,
            target_date=post_target,
            max_cloud_cover=cloud_max,
        )

    @staticmethod
    def _classify_dnbr(value: float) -> str:
        if value < 0.1:
            return "unburned"
        if value < 0.27:
            return "low"
        if value < 0.44:
            return "moderate_low"
        if value < 0.66:
            return "moderate_high"
        return "high"

    @staticmethod
    def _quality_score(cloud_cover: float) -> str:
        if cloud_cover <= 10:
            return "excellent"
        if cloud_cover <= 20:
            return "good"
        if cloud_cover <= 30:
            return "fair"
        if cloud_cover <= 50:
            return "poor"
        return "unusable"

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
    def _dnbr_id(pre_id: str, post_id: str) -> str:
        raw = f"{pre_id}:{post_id}"
        if len(raw) <= 92:
            return f"DNBR:{raw}"
        digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()
        return f"DNBR:{digest}"

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
        fire_id: str,
        label: str,
        acquisition_date: Optional[date],
        image_bytes: bytes,
        metadata: Dict[str, str],
    ):
        date_str = (
            acquisition_date.strftime("%Y%m%d") if acquisition_date else "unknown"
        )
        key = f"historic/{fire_id}/{label}_{date_str}.png"
        return self._storage.upload_bytes(
            data=image_bytes,
            key=key,
            bucket=os.environ.get("STORAGE_BUCKET_IMAGES", "forestguard-images"),
            content_type="image/png",
            metadata=metadata,
        )

    def _update_fire(self, fire_id: str, processing_error: Optional[str] = None):
        fire_key = self._normalize_fire_id(fire_id)
        fire = self.db.query(FireEvent).filter(FireEvent.id == fire_key).first()
        if not fire:
            return
        fire.has_historic_report = True
        if processing_error is not None:
            fire.processing_error = processing_error
        else:
            fire.processing_error = None

    def _update_episode_dnbr(
        self, fire_id: str, dnbr_value: float, severity_class: str
    ) -> None:
        episode_ids = (
            self.db.query(FireEpisodeEvent.episode_id)
            .filter(FireEpisodeEvent.event_id == self._normalize_fire_id(fire_id))
            .all()
        )
        if not episode_ids:
            return
        ids = [row[0] for row in episode_ids]
        query = text(
            """
                UPDATE fire_episodes
                   SET dnbr_severity = :dnbr,
                       severity_class = :severity,
                       dnbr_calculated_at = NOW()
                 WHERE id IN :ids
                """
        ).bindparams(bindparam("ids", expanding=True))
        self.db.execute(
            query,
            {"dnbr": dnbr_value, "severity": severity_class, "ids": ids},
        )

    def run(self, max_fires: Optional[int] = None) -> Dict[str, Any]:
        self._gee.authenticate()

        max_fires = max_fires or 50
        min_area = self._resolve_min_area()
        cloud_max = min(self._resolve_cloud_max(), DEFAULT_CLOUD_MAX)
        cloud_masking = self._resolve_cloud_masking()
        max_retry_days = self._resolve_max_retry_days()

        fires = self._fetch_candidates(max_fires, min_area, max_retry_days)
        if not fires:
            return {"processed": 0, "updated": 0, "skipped": 0, "errors": []}

        updated = 0
        skipped = 0
        errors: List[Dict[str, Any]] = []

        for fire in fires:
            try:
                bbox = self._bbox_from_point(fire.lat, fire.lon)
                start_date = fire.start_date.date()
                extinguished_date = fire.extinguished_at.date()

                try:
                    pre_image = self._select_pre_image(bbox, start_date, cloud_max)
                except GEEImageNotFoundError:
                    pre_image = None

                try:
                    post_image = self._select_post_image(
                        bbox, extinguished_date, cloud_max
                    )
                except GEEImageNotFoundError:
                    post_image = None

                if not pre_image or not post_image:
                    age_days = (date.today() - extinguished_date).days
                    if age_days >= max_retry_days:
                        self._update_fire(
                            fire.id,
                            processing_error="closure_report_incomplete: persistent cloud cover",
                        )
                        self.db.commit()
                        updated += 1
                    else:
                        skipped += 1
                    continue

                pre_meta = self._gee.get_image_metadata(pre_image)
                post_meta = self._gee.get_image_metadata(post_image)

                if cloud_masking:
                    pre_image = self._gee.apply_cloud_mask(pre_image)
                    post_image = self._gee.apply_cloud_mask(post_image)

                pre_nbr = (
                    self._gee.calculate_nbr(pre_image, bbox).get("mean", 0.0) or 0.0
                )
                post_nbr = (
                    self._gee.calculate_nbr(post_image, bbox).get("mean", 0.0) or 0.0
                )
                dnbr_value = float(pre_nbr) - float(post_nbr)
                severity_class = self._classify_dnbr(dnbr_value)

                slides: List[Dict[str, Any]] = []
                image_rows: List[SatelliteImage] = []

                def handle_image(
                    label: str,
                    image,
                    vis_type: str,
                    image_type: str,
                    metadata_source,
                ):
                    thumb_bytes = self._gee.download_thumbnail(
                        image,
                        bbox,
                        vis_type=vis_type,
                        dimensions=THUMB_DIMENSIONS,
                        format="png",
                    )
                    metadata = self._build_metadata(
                        gee_system_index=metadata_source.image_id,
                        vis_type=vis_type,
                        acquisition_date=metadata_source.acquisition_date,
                        cloud_cover_pct=metadata_source.cloud_cover_percent,
                        bbox=bbox,
                    )
                    upload = self._upload_thumbnail(
                        fire.id,
                        label,
                        metadata_source.acquisition_date,
                        thumb_bytes,
                        metadata,
                    )

                    quality = self._quality_score(
                        float(metadata_source.cloud_cover_percent)
                    )
                    days_after_fire = (
                        (metadata_source.acquisition_date - start_date).days
                        if metadata_source.acquisition_date
                        else None
                    )

                    slides.append(
                        {
                            "type": label,
                            "title": label.replace("_", " ").upper(),
                            "url": upload.url,
                            "description": f"Nubes: {metadata_source.cloud_cover_percent:.0f}%",
                            "date": metadata_source.acquisition_date.isoformat()
                            if metadata_source.acquisition_date
                            else None,
                        }
                    )

                    image_rows.append(
                        SatelliteImage(
                            fire_event_id=self._normalize_fire_id(fire.id),
                            satellite=metadata_source.satellite,
                            tile_id=metadata_source.tile_id,
                            product_id=metadata_source.image_id,
                            acquisition_date=metadata_source.acquisition_date
                            or date.today(),
                            image_type=image_type,
                            days_after_fire=days_after_fire,
                            cloud_cover_pct=float(metadata_source.cloud_cover_percent),
                            quality_score=quality,
                            usable_for_analysis=quality != "unusable",
                            r2_bucket=os.environ.get(
                                "STORAGE_BUCKET_IMAGES", "forestguard-images"
                            ),
                            r2_key=upload.key,
                            r2_url=upload.url,
                            thumbnail_url=upload.url,
                            file_size_mb=round(upload.size_bytes / (1024 * 1024), 4),
                            bands_included=VISUALS[vis_type]["bands"],
                            processing_level=metadata_source.processing_level
                            if hasattr(metadata_source, "processing_level")
                            else "L2A",
                            spatial_resolution_meters=VISUALS[vis_type].get(
                                "spatial_resolution", 10
                            ),
                            gee_system_index=metadata_source.image_id,
                            visualization_params=VISUALS[vis_type],
                            is_reproducible=True,
                        )
                    )

                handle_image("rgb_pre", pre_image, "RGB", "closure_pre_rgb", pre_meta)
                handle_image(
                    "rgb_post", post_image, "RGB", "closure_post_rgb", post_meta
                )
                handle_image("nbr_pre", pre_image, "NBR", "closure_pre_nbr", pre_meta)
                handle_image(
                    "nbr_post", post_image, "NBR", "closure_post_nbr", post_meta
                )

                try:
                    dnbr_id = self._dnbr_id(pre_meta.image_id, post_meta.image_id)
                    dnbr_bytes = self._gee.download_dnbr_thumbnail(
                        pre_image,
                        post_image,
                        bbox,
                        dimensions=THUMB_DIMENSIONS,
                        format="png",
                    )
                    dnbr_meta = self._build_metadata(
                        gee_system_index=dnbr_id,
                        vis_type="DNBR",
                        acquisition_date=post_meta.acquisition_date,
                        bbox=bbox,
                        dnbr_value=dnbr_value,
                        pre_image_id=pre_meta.image_id,
                        post_image_id=post_meta.image_id,
                    )
                    upload = self._upload_thumbnail(
                        fire.id,
                        "dnbr",
                        post_meta.acquisition_date,
                        dnbr_bytes,
                        dnbr_meta,
                    )

                    slides.append(
                        {
                            "type": "dnbr",
                            "title": "DNBR",
                            "url": upload.url,
                            "description": f"dNBR: {dnbr_value:.3f} ({severity_class})",
                            "date": post_meta.acquisition_date.isoformat()
                            if post_meta.acquisition_date
                            else None,
                        }
                    )

                    visualization_params = dict(VISUALS["DNBR"])
                    visualization_params["pre_image_id"] = pre_meta.image_id
                    visualization_params["post_image_id"] = post_meta.image_id

                    image_rows.append(
                        SatelliteImage(
                            fire_event_id=self._normalize_fire_id(fire.id),
                            satellite=post_meta.satellite,
                            tile_id=post_meta.tile_id,
                            product_id=dnbr_id,
                            acquisition_date=post_meta.acquisition_date or date.today(),
                            image_type="closure_dnbr",
                            days_after_fire=(
                                (post_meta.acquisition_date - start_date).days
                                if post_meta.acquisition_date
                                else None
                            ),
                            cloud_cover_pct=float(post_meta.cloud_cover_percent),
                            quality_score=self._quality_score(
                                float(post_meta.cloud_cover_percent)
                            ),
                            usable_for_analysis=True,
                            r2_bucket=os.environ.get(
                                "STORAGE_BUCKET_IMAGES", "forestguard-images"
                            ),
                            r2_key=upload.key,
                            r2_url=upload.url,
                            thumbnail_url=upload.url,
                            file_size_mb=round(upload.size_bytes / (1024 * 1024), 4),
                            bands_included=VISUALS["DNBR"]["bands"],
                            processing_level=post_meta.processing_level
                            if hasattr(post_meta, "processing_level")
                            else "L2A",
                            spatial_resolution_meters=VISUALS["DNBR"].get(
                                "spatial_resolution", 20
                            ),
                            gee_system_index=dnbr_id,
                            visualization_params=visualization_params,
                            is_reproducible=True,
                        )
                    )
                except Exception as exc:
                    logger.warning(
                        "Failed to generate dNBR thumbnail for %s: %s", fire.id, exc
                    )

                for row in image_rows:
                    self.db.add(row)

                self._update_episode_dnbr(fire.id, dnbr_value, severity_class)
                self._update_fire(fire.id)
                self.db.commit()
                updated += 1
            except (GEEAuthenticationError, GEERateLimitError) as exc:
                logger.exception("GEE error for fire %s: %s", fire.id, exc)
                self.db.rollback()
                raise
            except Exception as exc:
                logger.exception("Closure report failed for fire %s: %s", fire.id, exc)
                self.db.rollback()
                errors.append({"fire_id": fire.id, "error": str(exc)})

        return {
            "processed": len(fires),
            "updated": updated,
            "skipped": skipped,
            "errors": errors,
        }
