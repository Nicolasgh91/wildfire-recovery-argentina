from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import relationship

from app.models.base import Base
from app.models.clustering import ClusteringVersion  # noqa: F401


class FireEpisode(Base):
    __tablename__ = "fire_episodes"

    id = Column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )

    status = Column(String(20), server_default=text("'active'"))
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True))
    last_seen_at = Column(DateTime(timezone=True))

    centroid_lat = Column(Numeric)
    centroid_lon = Column(Numeric)
    bbox_minx = Column(Numeric)
    bbox_miny = Column(Numeric)
    bbox_maxx = Column(Numeric)
    bbox_maxy = Column(Numeric)
    provinces = Column(ARRAY(String))

    event_count = Column(Integer, default=0)
    detection_count = Column(Integer, default=0)
    frp_sum = Column(Numeric)
    frp_max = Column(Numeric)
    estimated_area_hectares = Column(Numeric)

    gee_candidate = Column(Boolean, default=False)
    gee_priority = Column(Integer)
    last_gee_image_id = Column(String)
    last_update_sat = Column(DateTime(timezone=True))
    slides_data = Column(JSONB)

    clustering_version_id = Column(
        UUID(as_uuid=True), ForeignKey("clustering_versions.id")
    )
    requires_recalculation = Column(Boolean, default=False)
    dnbr_severity = Column(Numeric)
    severity_class = Column(String(20))
    dnbr_calculated_at = Column(DateTime(timezone=True))

    created_at = Column(DateTime(timezone=True), server_default=text("now()"))
    updated_at = Column(DateTime(timezone=True), server_default=text("now()"))

    events = relationship(
        "FireEpisodeEvent",
        back_populates="episode",
        cascade="all, delete-orphan",
    )


class FireEpisodeEvent(Base):
    __tablename__ = "fire_episode_events"

    episode_id = Column(
        UUID(as_uuid=True),
        ForeignKey("fire_episodes.id", ondelete="CASCADE"),
        primary_key=True,
    )
    event_id = Column(
        UUID(as_uuid=True),
        ForeignKey("fire_events.id", ondelete="CASCADE"),
        primary_key=True,
    )
    added_at = Column(DateTime(timezone=True), server_default=text("now()"))

    episode = relationship("FireEpisode", back_populates="events")
