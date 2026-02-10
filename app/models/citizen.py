from geoalchemy2 import Geography
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base, TimestampMixin, UUIDMixin


class CitizenReport(Base, UUIDMixin, TimestampMixin):
    """
    Denuncias ciudadanas sobre actividad ilegal en áreas afectadas por incendios.
    UC-09: Soporte a Denuncias Ciudadanas
    """

    __tablename__ = "citizen_reports"

    # Reported location
    reported_location = Column(
        Geography(geometry_type="POINT", srid=4326), nullable=False, index=True
    )
    reported_latitude = Column(Float(precision=6), nullable=False)
    reported_longitude = Column(Float(precision=6), nullable=False)
    location_description = Column(Text)

    # Report type
    report_type = Column(String(50), index=True)

    # Description
    description = Column(Text, nullable=False)
    observed_date = Column(Date)

    # User evidence
    user_photos = Column(ARRAY(Text))  # URLs of uploaded photos

    # Reporter information
    reporter_name = Column(String(200))
    reporter_email = Column(String(255))
    reporter_phone = Column(String(50))
    is_anonymous = Column(Boolean, default=False)
    reporter_organization = Column(String(200))

    # Auto-cross with system data
    related_fire_events = Column(ARRAY(UUID(as_uuid=True)))
    related_protected_areas = Column(ARRAY(UUID(as_uuid=True)))
    historical_fires_in_area = Column(Integer)

    # Evidence package
    evidence_package_url = Column(Text)

    # Status
    status = Column(String(50), default="submitted", index=True)

    # Follow-up
    reviewed_by = Column(String(100))
    reviewed_at = Column(DateTime(timezone=True))
    authority_notified = Column(String(200))
    authority_notified_at = Column(DateTime(timezone=True))
    internal_notes = Column(Text)

    # Privacy
    is_public = Column(Boolean, default=False, index=True)

    def __repr__(self):
        return f"<CitizenReport(id={self.id}, type={self.report_type}, status={self.status})>"


class LandUseChange(Base, UUIDMixin, TimestampMixin):
    """
    Cambios detectados en el uso del suelo post-incendio (posibles violaciones).
    UC-08: Detección de Cambio de Uso Post-Incendio
    """

    __tablename__ = "land_use_changes"

    # Foreign keys
    fire_event_id = Column(
        UUID(as_uuid=True), ForeignKey("fire_events.id"), nullable=False, index=True
    )
    monitoring_record_id = Column(
        UUID(as_uuid=True), ForeignKey("vegetation_monitoring.id")
    )

    # Detection
    change_detected_at = Column(Date, nullable=False)
    months_after_fire = Column(Integer)

    # Change type
    change_type = Column(String(50), nullable=False)
    change_severity = Column(String(20))  # 'low', 'medium', 'high', 'critical'

    # Visual evidence
    before_image_id = Column(UUID(as_uuid=True), ForeignKey("satellite_images.id"))
    after_image_id = Column(UUID(as_uuid=True), ForeignKey("satellite_images.id"))
    change_detection_image_url = Column(Text)

    # Analysis
    affected_area_hectares = Column(Float)
    is_potential_violation = Column(Boolean, default=False, index=True)
    violation_confidence = Column(String(20))

    # Status
    status = Column(String(50), default="pending_review", index=True)

    # Follow-up
    reviewed_by = Column(String(100))
    reviewed_at = Column(DateTime(timezone=True))
    notes = Column(Text)

    # Relationships
    fire_event = relationship("FireEvent", back_populates="land_use_changes")
    monitoring_record = relationship(
        "VegetationMonitoring", back_populates="land_use_change"
    )
    before_image = relationship("SatelliteImage", foreign_keys=[before_image_id])
    after_image = relationship("SatelliteImage", foreign_keys=[after_image_id])

    def __repr__(self):
        return f"<LandUseChange(fire={self.fire_event_id}, type={self.change_type}, status={self.status})>"
