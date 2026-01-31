from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base, TimestampMixin, UUIDMixin


class ParkAlert(Base, UUIDMixin, TimestampMixin):
    """
    Alertas de capacidad de carga en parques (UC-04).
    """

    __tablename__ = "park_alerts"

    protected_area_id = Column(UUID(as_uuid=True), ForeignKey("protected_areas.id"), nullable=False)
    alert_date = Column(Date, nullable=False)

    visitor_count = Column(Integer, nullable=False)
    carrying_capacity = Column(Integer, nullable=False)
    occupancy_pct = Column(Float, nullable=False)

    risk_score = Column(Float, nullable=False)
    risk_level = Column(String(20), nullable=False)  # low, medium, high
    alert_level = Column(String(20), nullable=False)  # normal, watch, alert

    climate_summary = Column(Text)
    recommended_action = Column(Text)
    is_acknowledged = Column(Boolean, default=False)
    acknowledged_by = Column(String(100))
    acknowledged_at = Column(DateTime(timezone=True))

    protected_area = relationship("ProtectedArea")

    def __repr__(self) -> str:
        return (
            f"<ParkAlert(area={self.protected_area_id}, date={self.alert_date}, "
            f"level={self.alert_level})>"
        )
