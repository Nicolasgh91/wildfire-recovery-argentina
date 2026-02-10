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
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base, TimestampMixin, UUIDMixin


class LandUseAudit(Base, UUIDMixin, TimestampMixin):
    """
    Log de consultas de usuarios sobre cambio de uso del suelo.
    UC-01: Auditoría Anti-Loteo
    """

    __tablename__ = "land_use_audits"

    # Query parameters
    queried_latitude = Column(Float(precision=6), nullable=False)
    queried_longitude = Column(Float(precision=6), nullable=False)
    queried_location = Column(
        Geography(geometry_type="POINT", srid=4326), nullable=False, index=True
    )
    search_radius_meters = Column(Integer, default=500)

    # Timestamp
    queried_at = Column(DateTime(timezone=True), default=func.now(), index=True)

    # Results
    fires_found = Column(Integer, default=0)
    earliest_fire_date = Column(DateTime(timezone=True))
    latest_fire_date = Column(DateTime(timezone=True))
    prohibition_until = Column(Date, index=True)
    is_violation = Column(Boolean, default=False, index=True)
    violation_severity = Column(
        String(20)
    )  # 'none', 'low', 'medium', 'high', 'critical'

    # Evidence generated
    report_generated = Column(Boolean, default=False)
    report_pdf_url = Column(Text)
    report_json = Column(JSONB)  # Full JSON response for audit trail

    # User metadata (optional, for analytics and rate limiting)
    user_ip = Column(INET, index=True)
    user_agent = Column(Text)
    api_key_id = Column(UUID(as_uuid=True))

    # Performance metrics
    query_duration_ms = Column(Integer)

    # Relationships
    certificate = relationship("LandCertificate", back_populates="audit", uselist=False)

    def __repr__(self):
        return f"<LandUseAudit(id={self.id}, location=({self.queried_latitude}, {self.queried_longitude}), fires={self.fires_found})>"


class LandCertificate(Base, UUIDMixin, TimestampMixin):
    """
    Certificados de condición legal del terreno emitidos por la API.
    UC-07: Certificación Legal
    """

    __tablename__ = "land_certificates"

    # Reference to audit
    audit_id = Column(
        UUID(as_uuid=True), ForeignKey("land_use_audits.id"), nullable=False
    )

    # Land information
    queried_location = Column(
        Geography(geometry_type="POINT", srid=4326), nullable=False, index=True
    )
    cadastral_id = Column(String(100))
    address = Column(Text)

    # Legal result
    is_legally_exploitable = Column(Boolean, nullable=False)
    legal_status = Column(String(50))  # 'clear', 'prohibited_protected_area', etc.

    # Evidence
    fire_events_affecting = Column(JSONB)  # Array of fire_event_ids with dates
    earliest_prohibition_date = Column(Date)
    prohibition_expires_on = Column(Date)

    # Certificate metadata
    certificate_number = Column(String(50), unique=True, nullable=False, index=True)
    issued_at = Column(DateTime(timezone=True), default=func.now())
    valid_until = Column(DateTime(timezone=True), index=True)

    # Anti-forgery verification
    verification_hash = Column(String(64), nullable=False)  # SHA256
    pdf_url = Column(Text)
    qr_code_url = Column(Text)

    # Requester
    requester_email = Column(String(255))
    requester_organization = Column(String(200))

    # Relationships
    audit = relationship("LandUseAudit", back_populates="certificate")

    def __repr__(self):
        return f"<LandCertificate(number={self.certificate_number}, status={self.legal_status})>"
