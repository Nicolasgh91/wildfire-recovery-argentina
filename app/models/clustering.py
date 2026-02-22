from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base


class ClusteringVersion(Base):
    __tablename__ = "clustering_versions"

    id = Column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    version_name = Column(String(50), nullable=False)
    epsilon_km = Column(Numeric, nullable=False)
    min_points = Column(Integer, nullable=False)
    temporal_window_hours = Column(Integer, nullable=False)
    algorithm = Column(String(20), nullable=False, server_default=text("'ST-DBSCAN'"))
    created_at = Column(DateTime(timezone=True), server_default=text("now()"))
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    is_active = Column(Boolean, server_default=text("true"))
    change_reason = Column(Text)

    __table_args__ = (
        CheckConstraint(
            "epsilon_km > 0 AND epsilon_km <= 100",
            name="clustering_versions_epsilon_check",
        ),
        CheckConstraint(
            "min_points >= 1 AND min_points <= 100",
            name="clustering_versions_min_points_check",
        ),
        CheckConstraint(
            "temporal_window_hours >= 1",
            name="clustering_versions_temporal_window_check",
        ),
    )


class EpisodeMerger(Base):
    __tablename__ = "episode_mergers"

    id = Column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    absorbed_episode_id = Column(
        UUID(as_uuid=True),
        ForeignKey("fire_episodes.id", ondelete="RESTRICT"),
        nullable=False,
    )
    absorbing_episode_id = Column(
        UUID(as_uuid=True),
        ForeignKey("fire_episodes.id", ondelete="RESTRICT"),
        nullable=False,
    )
    merged_at = Column(DateTime(timezone=True), server_default=text("now()"))
    reason = Column(String(50), nullable=False)
    merged_by_version_id = Column(
        UUID(as_uuid=True), ForeignKey("clustering_versions.id")
    )
    notes = Column(Text)

    __table_args__ = (
        CheckConstraint(
            "reason IN ('spatial_overlap', 'temporal_continuity', 'manual_merge', 'algorithm_update')",
            name="episode_mergers_reason_check",
        ),
        CheckConstraint(
            "absorbed_episode_id != absorbing_episode_id",
            name="episode_mergers_different_episodes_check",
        ),
    )
