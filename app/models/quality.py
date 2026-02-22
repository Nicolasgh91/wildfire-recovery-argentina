from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.sql import func

from .base import Base, TimestampMixin, UUIDMixin


class DataSourceMetadata(Base, UUIDMixin, TimestampMixin):
    """
    Metadata sobre fuentes de datos para transparencia y confiabilidad.
    UC-11: Evaluación de Confiabilidad del Dato
    """

    __tablename__ = "data_source_metadata"

    # Source identification
    source_name = Column(String(100), unique=True, nullable=False)
    source_type = Column(
        String(50)
    )  # 'satellite', 'reanalysis', 'ground_station', 'manual'

    # Technical characteristics
    spatial_resolution_meters = Column(Integer)
    temporal_resolution_hours = Column(Integer)
    coverage_area = Column(Text)

    # Reliability
    typical_accuracy_percentage = Column(Float(precision=1))
    known_limitations = Column(Text)

    # Legal
    is_admissible_in_court = Column(Boolean)
    legal_precedent_cases = Column(ARRAY(Text))

    # Metadata
    data_provider = Column(String(200))
    provider_url = Column(Text)
    documentation_url = Column(Text)
    last_updated = Column(DateTime(timezone=True), default=func.now())

    def __repr__(self):
        return f"<DataSourceMetadata(name={self.source_name}, type={self.source_type})>"
