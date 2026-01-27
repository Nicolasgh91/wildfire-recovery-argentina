from sqlalchemy import Column, Date, DateTime , Float, ForeignKey, SmallInteger, String
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin, UUIDMixin


class ClimateData(Base, UUIDMixin, TimestampMixin):
    """
    Datos climáticos históricos de ERA5-Land (Open-Meteo) 
    para contexto forense (UC-02).
    """
    
    __tablename__ = 'climate_data'
    
    # Spatiotemporal reference
    reference_date = Column(Date, nullable=False, index=True)
    latitude = Column(Float(precision=3), nullable=False)   # Rounded to ~100m
    longitude = Column(Float(precision=3), nullable=False)
    spatial_cluster_id = Column(String(20), index=True)  # H3 hexagon or grid cell
    
    # Critical variables for forensic analysis
    temp_max_celsius = Column(Float(precision=1))
    temp_min_celsius = Column(Float(precision=1))
    temp_mean_celsius = Column(Float(precision=1))
    wind_speed_kmh = Column(Float(precision=1))
    wind_direction_degrees = Column(SmallInteger)
    wind_gusts_kmh = Column(Float(precision=1))
    precipitation_mm = Column(Float(precision=1))
    relative_humidity_pct = Column(SmallInteger)
    
    # Drought/fire risk indices
    kbdi = Column(Float(precision=1))  # Keetch-Byram Drought Index
    
    # Metadata
    data_source = Column(String(50), default='ERA5-Land')
    query_timestamp = Column(DateTime(timezone=True), default=func.now())
    
    # Relationships
    fire_associations = relationship("FireClimateAssociation", back_populates="climate_data")
    
    def __repr__(self):
        return f"<ClimateData(date={self.reference_date}, lat={self.latitude}, lon={self.longitude})>"


class FireClimateAssociation(Base, TimestampMixin):
    """
    Relación muchos-a-uno entre eventos de incendio y datos climáticos.
    """
    
    __tablename__ = 'fire_climate_associations'
    
    # Primary key is fire_event_id (one-to-one from FireEvent perspective)
    fire_event_id = Column(
        UUID(as_uuid=True), 
        ForeignKey('fire_events.id', ondelete='CASCADE'), 
        primary_key=True
    )
    climate_data_id = Column(UUID(as_uuid=True), ForeignKey('climate_data.id'), nullable=False)
    
    # Association metadata
    distance_meters = Column(Float)
    assignment_method = Column(String(50), default='spatial_cluster')
    
    # Relationships
    fire_event = relationship("FireEvent", back_populates="climate_association")
    climate_data = relationship("ClimateData", back_populates="fire_associations")
    
    def __repr__(self):
        return f"<FireClimateAssoc(fire={self.fire_event_id}, climate={self.climate_data_id})>"
