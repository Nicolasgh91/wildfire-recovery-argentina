from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base, TimestampMixin, UUIDMixin


class Shelter(Base, UUIDMixin, TimestampMixin):
    """
    Refugios/puestos de montaña para registro de visitantes (UC-12).
    """

    __tablename__ = "shelters"

    name = Column(String(255), nullable=False, index=True)
    province = Column(String(100), nullable=False, index=True)
    location_description = Column(Text)
    carrying_capacity = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True, index=True)

    visitor_logs = relationship("VisitorLog", back_populates="shelter")

    def __repr__(self) -> str:
        return f"<Shelter(name={self.name}, province={self.province})>"


class VisitorLog(Base, UUIDMixin, TimestampMixin):
    """
    Registro principal de visitantes (UC-12).
    """

    __tablename__ = "visitor_logs"

    shelter_id = Column(UUID(as_uuid=True), ForeignKey("shelters.id"), nullable=False, index=True)
    visit_date = Column(Date, nullable=False, index=True)
    registration_type = Column(String(20), nullable=False)  # day_entry | overnight

    group_leader_name = Column(String(255), nullable=False)
    group_leader_document = Column(String(100))
    contact_email = Column(String(255))
    contact_phone = Column(String(50))

    total_people = Column(Integer, nullable=False)
    first_submitted_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    shelter = relationship("Shelter", back_populates="visitor_logs")
    companions = relationship("VisitorLogCompanion", back_populates="visitor_log", cascade="all, delete-orphan")
    revisions = relationship("VisitorLogRevision", back_populates="visitor_log", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<VisitorLog(id={self.id}, date={self.visit_date}, total={self.total_people})>"


class VisitorLogCompanion(Base, UUIDMixin, TimestampMixin):
    """
    Integrantes de un grupo de visitantes (UC-12).
    """

    __tablename__ = "visitor_log_companions"

    visitor_log_id = Column(UUID(as_uuid=True), ForeignKey("visitor_logs.id"), nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    age_range = Column(String(50))
    document = Column(String(100))

    visitor_log = relationship("VisitorLog", back_populates="companions")

    def __repr__(self) -> str:
        return f"<VisitorLogCompanion(name={self.full_name})>"


class VisitorLogRevision(Base, UUIDMixin, TimestampMixin):
    """
    Historial de ediciones para registros de visitantes (UC-12).
    """

    __tablename__ = "visitor_log_revisions"

    visitor_log_id = Column(UUID(as_uuid=True), ForeignKey("visitor_logs.id"), nullable=False, index=True)
    changed_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    changed_by = Column(String(100))
    changes = Column(Text, nullable=False)

    visitor_log = relationship("VisitorLog", back_populates="revisions")

    def __repr__(self) -> str:
        return f"<VisitorLogRevision(log={self.visitor_log_id}, changed_at={self.changed_at})>"
