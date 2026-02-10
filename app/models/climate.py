from geoalchemy2 import Geography
from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base, UUIDMixin


class ClimateData(Base, UUIDMixin):
    """
    Datos climaticos de Open-Meteo (ERA5-Land)
    para contexto forense (UC-F04).
    """

    __tablename__ = "climate_data"

    location = Column(Geography(geometry_type="POINT", srid=4326), nullable=False)
    latitude = Column(Numeric(10, 6), nullable=False)
    longitude = Column(Numeric(10, 6), nullable=False)
    recorded_at = Column(DateTime(timezone=True), nullable=False)

    data_source = Column(String(50), nullable=False, server_default="open-meteo")
    source_dataset = Column(String(100))

    temperature_2m = Column(Numeric(5, 2))
    relative_humidity_2m = Column(Numeric(5, 2))
    wind_speed_10m = Column(Numeric(6, 2))
    wind_direction_10m = Column(Integer)
    wind_gusts_10m = Column(Numeric(6, 2))
    precipitation = Column(Numeric(6, 2))

    soil_moisture_0_to_10cm = Column(Numeric(5, 4))
    evapotranspiration = Column(Numeric(6, 2))
    vapor_pressure_deficit = Column(Numeric(6, 2))

    fire_weather_index = Column(Numeric(6, 2))
    drought_code = Column(Numeric(6, 2))

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    fire_associations = relationship(
        "FireClimateAssociation", back_populates="climate_data"
    )

    def __repr__(self):
        return (
            f"<ClimateData(recorded_at={self.recorded_at}, "
            f"lat={self.latitude}, lon={self.longitude})>"
        )


class FireClimateAssociation(Base, UUIDMixin):
    """
    Relación N:M entre eventos de incendio y datos climáticos.
    """

    __tablename__ = "fire_climate_associations"

    fire_event_id = Column(
        UUID(as_uuid=True),
        ForeignKey("fire_events.id", ondelete="CASCADE"),
        nullable=False,
    )
    climate_data_id = Column(
        UUID(as_uuid=True),
        ForeignKey("climate_data.id", ondelete="CASCADE"),
        nullable=False,
    )

    association_type = Column(String(30), nullable=False, server_default="during")
    hours_offset = Column(Integer)
    distance_km = Column(Numeric(8, 2))
    relevance_weight = Column(Numeric(3, 2), server_default="1.0")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    fire_event = relationship("FireEvent", back_populates="climate_associations")
    climate_data = relationship("ClimateData", back_populates="fire_associations")

    def __repr__(self):
        return f"<FireClimateAssoc(fire={self.fire_event_id}, climate={self.climate_data_id})>"
