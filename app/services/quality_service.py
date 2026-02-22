from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import case, desc, func, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.climate import FireClimateAssociation
from app.models.evidence import SatelliteImage, VegetationMonitoring
from app.models.episode import FireEpisodeEvent
from app.models.fire import FireDetection, FireEvent
from app.models.quality import DataSourceMetadata
from app.schemas.fire import FireStatus
from app.schemas.quality import (
    QualityClass,
    QualityLimitation,
    QualityMetrics,
    QualityResponse,
    QualitySource,
    SeverityLevel,
)

logger = logging.getLogger(__name__)

DEFAULT_WEIGHTS: Dict[str, float] = {
    "detections": 0.4,
    "imagery": 0.2,
    "climate": 0.2,
    "independent": 0.2,
}

HIGH_SCORE_THRESHOLD = 80.0
MEDIUM_SCORE_THRESHOLD = 50.0
METADATA_PENALTY = 5.0


class QualityService:
    """Service for data quality scoring and explanations."""
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _to_float(value: object, default: float = 0.0) -> float:
        if value is None:
            return default
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _clamp_score(value: float) -> float:
        if value < 0:
            return 0.0
        if value > 100:
            return 100.0
        return value

    @staticmethod
    def _independent_score(independent_sources: int) -> float:
        if independent_sources >= 2:
            return 100.0
        if independent_sources == 1:
            return 50.0
        return 0.0

    @classmethod
    def _classify_score(cls, score: float) -> QualityClass:
        if score >= HIGH_SCORE_THRESHOLD:
            return QualityClass.HIGH
        if score >= MEDIUM_SCORE_THRESHOLD:
            return QualityClass.MEDIUM
        return QualityClass.LOW

    @classmethod
    def _compute_reliability_score(
        cls,
        confidence_score: float,
        imagery_score: float,
        climate_score: float,
        independent_score: float,
        weights: Dict[str, float],
    ) -> float:
        detections_weight = weights.get("detections", DEFAULT_WEIGHTS["detections"])
        imagery_weight = weights.get("imagery", DEFAULT_WEIGHTS["imagery"])
        climate_weight = weights.get("climate", DEFAULT_WEIGHTS["climate"])
        independent_weight = weights.get("independent", DEFAULT_WEIGHTS["independent"])

        score = (
            confidence_score * detections_weight
            + imagery_score * imagery_weight
            + climate_score * climate_weight
            + independent_score * independent_weight
        )
        return cls._clamp_score(score)

    def _load_weights(self) -> Dict[str, float]:
        weights = dict(DEFAULT_WEIGHTS)
        try:
            row = (
                self.db.execute(
                    text(
                        "SELECT param_value FROM system_parameters WHERE param_key = :key"
                    ),
                    {"key": "quality_weights"},
                )
                .mappings()
                .first()
            )
        except SQLAlchemyError as exc:
            logger.warning("quality_weights lookup failed: %s", exc)
            return weights

        if not row:
            return weights

        param_value = row.get("param_value")
        if isinstance(param_value, dict):
            for key in weights:
                if key not in param_value:
                    continue
                try:
                    weights[key] = float(param_value[key])
                except (TypeError, ValueError):
                    continue
        return weights

    def _fetch_quality_metrics(self, fire_event_id: UUID) -> Optional[dict]:
        try:
            row = (
                self.db.execute(
                    text(
                        """
                        SELECT fire_event_id,
                               start_date,
                               province,
                               total_detections,
                               avg_confidence,
                               detection_count,
                               independent_sources,
                               imagery_count,
                               has_imagery,
                               has_climate,
                               has_ndvi,
                               confidence_score,
                               imagery_score,
                               climate_score,
                               independent_score,
                               reliability_score,
                               score_calculated_at
                          FROM fire_event_quality_metrics
                         WHERE fire_event_id = :fire_event_id
                        """
                    ),
                    {"fire_event_id": str(fire_event_id)},
                )
                .mappings()
                .first()
            )
        except SQLAlchemyError as exc:
            logger.warning("quality view query failed: %s", exc)
            row = None

        if row:
            return dict(row)

        return self._compute_quality_from_tables(fire_event_id)

    def _compute_quality_from_tables(self, fire_event_id: UUID) -> Optional[dict]:
        fire = self.db.query(FireEvent).filter(FireEvent.id == fire_event_id).first()
        if not fire:
            return None

        detection_count = (
            self.db.query(func.count(FireDetection.id))
            .filter(FireDetection.fire_event_id == fire_event_id)
            .scalar()
            or 0
        )
        independent_sources = (
            self.db.query(func.count(func.distinct(FireDetection.satellite)))
            .filter(FireDetection.fire_event_id == fire_event_id)
            .scalar()
            or 0
        )
        imagery_count = (
            self.db.query(func.count(SatelliteImage.id))
            .filter(SatelliteImage.fire_event_id == fire_event_id)
            .scalar()
            or 0
        )
        climate_count = (
            self.db.query(func.count(FireClimateAssociation.fire_event_id))
            .filter(FireClimateAssociation.fire_event_id == fire_event_id)
            .scalar()
            or 0
        )
        ndvi_count = (
            self.db.query(func.count(VegetationMonitoring.id))
            .filter(VegetationMonitoring.fire_event_id == fire_event_id)
            .scalar()
            or 0
        )

        avg_confidence = self._to_float(fire.avg_confidence, 0.0)
        confidence_score = self._clamp_score(avg_confidence)
        imagery_score = 100.0 if imagery_count > 0 else 0.0
        climate_score = 100.0 if climate_count > 0 else 0.0
        independent_score = self._independent_score(independent_sources)
        weights = self._load_weights()
        reliability_score = self._compute_reliability_score(
            confidence_score,
            imagery_score,
            climate_score,
            independent_score,
            weights,
        )

        total_detections = (
            int(fire.total_detections)
            if fire.total_detections is not None
            else int(detection_count)
        )

        return {
            "fire_event_id": fire.id,
            "start_date": fire.start_date,
            "province": fire.province,
            "total_detections": total_detections,
            "avg_confidence": avg_confidence,
            "detection_count": int(detection_count),
            "independent_sources": int(independent_sources),
            "imagery_count": int(imagery_count),
            "has_imagery": imagery_count > 0,
            "has_climate": climate_count > 0,
            "has_ndvi": ndvi_count > 0,
            "confidence_score": confidence_score,
            "imagery_score": imagery_score,
            "climate_score": climate_score,
            "independent_score": independent_score,
            "reliability_score": reliability_score,
            "score_calculated_at": datetime.now(timezone.utc),
        }

    def _load_sources(
        self,
        has_imagery: bool,
        has_climate: bool,
        independent_sources: int,
    ) -> Tuple[List[QualitySource], bool]:
        try:
            rows = (
                self.db.query(DataSourceMetadata)
                .order_by(DataSourceMetadata.source_name.asc())
                .all()
            )
        except SQLAlchemyError as exc:
            logger.warning("data_source_metadata query failed: %s", exc)
            return [], True

        if not rows:
            return [], True

        sources: List[QualitySource] = []
        for row in rows:
            source_type = (row.source_type or "").lower()
            is_used: Optional[bool] = None

            if source_type == "satellite":
                is_used = has_imagery or independent_sources > 0
            elif source_type in {"reanalysis", "climate", "weather"}:
                is_used = has_climate

            sources.append(
                QualitySource(
                    source_name=row.source_name,
                    source_type=row.source_type,
                    spatial_resolution_meters=row.spatial_resolution_meters,
                    temporal_resolution_hours=row.temporal_resolution_hours,
                    coverage_area=row.coverage_area,
                    typical_accuracy_percentage=row.typical_accuracy_percentage,
                    known_limitations=row.known_limitations,
                    is_admissible_in_court=row.is_admissible_in_court,
                    legal_precedent_cases=row.legal_precedent_cases,
                    data_provider=row.data_provider,
                    provider_url=row.provider_url,
                    documentation_url=row.documentation_url,
                    last_updated=row.last_updated,
                    is_used=is_used,
                )
            )
        return sources, False

    def _build_limitations(
        self,
        avg_confidence: float,
        has_imagery: bool,
        has_climate: bool,
        independent_sources: int,
        metadata_missing: bool,
    ) -> Tuple[List[QualityLimitation], List[str]]:
        limitations: List[QualityLimitation] = []
        warnings: List[str] = []

        if not has_imagery:
            limitations.append(
                QualityLimitation(
                    code="no_imagery",
                    description="No satellite imagery associated.",
                    severity=SeverityLevel.MEDIUM,
                )
            )
            warnings.append("No satellite imagery available for this event.")

        if not has_climate:
            limitations.append(
                QualityLimitation(
                    code="no_climate",
                    description="No climate association available.",
                    severity=SeverityLevel.MEDIUM,
                )
            )
            warnings.append("No climate data linked to this event.")

        if avg_confidence < 50:
            limitations.append(
                QualityLimitation(
                    code="low_confidence",
                    description="Low average detection confidence.",
                    severity=SeverityLevel.LOW,
                )
            )

        if independent_sources < 2:
            limitations.append(
                QualityLimitation(
                    code="single_source",
                    description="Limited independent detections.",
                    severity=SeverityLevel.LOW,
                )
            )

        if metadata_missing:
            limitations.append(
                QualityLimitation(
                    code="metadata_missing",
                    description="Source metadata incomplete or missing.",
                    severity=SeverityLevel.MEDIUM,
                )
            )
            warnings.append("Source metadata is missing or incomplete.")

        return limitations, warnings

    def get_quality(self, fire_event_id: UUID) -> Optional[QualityResponse]:
        row = self._fetch_quality_metrics(fire_event_id)
        if not row:
            return None

        avg_confidence = self._to_float(row.get("avg_confidence"), 0.0)
        confidence_score = self._to_float(row.get("confidence_score"), avg_confidence)
        imagery_score = self._to_float(row.get("imagery_score"), 0.0)
        climate_score = self._to_float(row.get("climate_score"), 0.0)
        independent_score = self._to_float(row.get("independent_score"), 0.0)
        reliability_score = self._to_float(row.get("reliability_score"), 0.0)
        total_detections = int(row.get("total_detections") or 0)
        independent_sources = int(row.get("independent_sources") or 0)
        has_imagery = bool(row.get("has_imagery"))
        has_climate = bool(row.get("has_climate"))
        has_ndvi = bool(row.get("has_ndvi"))
        score_calculated_at = row.get("score_calculated_at") or datetime.now(
            timezone.utc
        )

        sources, metadata_missing = self._load_sources(
            has_imagery=has_imagery,
            has_climate=has_climate,
            independent_sources=independent_sources,
        )

        if metadata_missing:
            reliability_score -= METADATA_PENALTY
        reliability_score = self._clamp_score(reliability_score)

        limitations, warnings = self._build_limitations(
            avg_confidence=avg_confidence,
            has_imagery=has_imagery,
            has_climate=has_climate,
            independent_sources=independent_sources,
            metadata_missing=metadata_missing,
        )

        metrics = QualityMetrics(
            reliability_score=round(reliability_score, 2),
            classification=self._classify_score(reliability_score),
            confidence_score=round(self._clamp_score(confidence_score), 2),
            imagery_score=round(self._clamp_score(imagery_score), 2),
            climate_score=round(self._clamp_score(climate_score), 2),
            independent_score=round(self._clamp_score(independent_score), 2),
            avg_confidence=round(self._clamp_score(avg_confidence), 2),
            total_detections=total_detections,
            independent_sources=independent_sources,
            has_imagery=has_imagery,
            has_climate=has_climate,
            has_ndvi=has_ndvi,
            score_calculated_at=score_calculated_at,
        )

        return QualityResponse(
            fire_event_id=row["fire_event_id"],
            start_date=row["start_date"],
            province=row.get("province"),
            metrics=metrics,
            limitations=limitations,
            sources=sources,
            warnings=warnings,
        )

    def get_quality_by_episode(self, episode_id: UUID) -> Optional[QualityResponse]:
        representative_event = (
            self.db.query(FireEvent.id)
            .join(FireEpisodeEvent, FireEpisodeEvent.event_id == FireEvent.id)
            .filter(FireEpisodeEvent.episode_id == episode_id)
            .order_by(
                case(
                    (
                        FireEvent.status.in_(
                            [FireStatus.ACTIVE.value, FireStatus.MONITORING.value]
                        ),
                        0,
                    ),
                    else_=1,
                ),
                desc(FireEvent.end_date),
                desc(FireEvent.start_date),
            )
            .first()
        )

        if not representative_event:
            return None

        return self.get_quality(representative_event.id)
