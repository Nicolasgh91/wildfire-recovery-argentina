from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
    Time,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base, TimestampMixin, UUIDMixin


class SatelliteImage(Base, UUIDMixin, TimestampMixin):
    """
    Imágenes Sentinel-2 (pre/post fuego) almacenadas en el storage de objetos.
    """

    __tablename__ = "satellite_images"

    # Foreign key
    fire_event_id = Column(
        UUID(as_uuid=True),
        ForeignKey("fire_events.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Image identification
    satellite = Column(String(20), default="Sentinel-2")
    tile_id = Column(String(50))  # e.g., 21HUB
    product_id = Column(String(100))  # Full Copernicus product ID
    acquisition_date = Column(Date, nullable=False)
    acquisition_time = Column(Time)

    # Timing relative to fire
    days_after_fire = Column(Integer)  # Negative = pre-fire, positive = post-fire
    image_type = Column(String(20))  # 'pre_fire', 'post_fire', 'monthly_monitoring'

    # Quality
    cloud_cover_pct = Column(Float(precision=1))
    quality_score = Column(
        String(20)
    )  # 'excellent', 'good', 'fair', 'poor', 'unusable'
    usable_for_analysis = Column(Boolean, default=True)

    # Storage in object storage (GCS)
    r2_bucket = Column(String(100), default="forestguard-images")
    r2_key = Column(Text, nullable=False)  # 'fires/{fire_id}/sentinel2_{date}.tif'
    r2_url = Column(Text, nullable=False)
    thumbnail_url = Column(Text)
    file_size_mb = Column(Float(precision=2))

    # Processing
    bands_included = Column(ARRAY(Text))  # ['B04', 'B03', 'B02'] for RGB
    processing_level = Column(String(10), default="L2A")
    spatial_resolution_meters = Column(SmallInteger, default=10)

    # Reproducibility metadata
    gee_system_index = Column(String(100))
    visualization_params = Column(JSONB)
    is_reproducible = Column(Boolean, default=False)

    # Relationships
    fire_event = relationship("FireEvent", back_populates="satellite_images")
    vegetation_monitoring = relationship(
        "VegetationMonitoring", back_populates="satellite_image"
    )

    def __repr__(self):
        return f"<SatelliteImage(fire={self.fire_event_id}, date={self.acquisition_date}, type={self.image_type})>"


class VegetationMonitoring(Base, UUIDMixin, TimestampMixin):
    """
    Seguimiento mensual de recuperación de vegetación post-incendio (NDVI).
    UC-06: Reforestación
    """

    __tablename__ = "vegetation_monitoring"

    # Foreign keys
    fire_event_id = Column(
        UUID(as_uuid=True),
        ForeignKey("fire_events.id", ondelete="CASCADE"),
        nullable=False,
    )
    satellite_image_id = Column(UUID(as_uuid=True), ForeignKey("satellite_images.id"))

    # Temporal
    month_number = Column(SmallInteger)  # 1-36 (up to 3 years)
    monitoring_date = Column(Date, nullable=False)
    months_after_fire = Column(Integer)

    # NDVI metrics
    ndvi_mean = Column(Float(precision=3))  # -1 to 1
    ndvi_min = Column(Float(precision=3))
    ndvi_max = Column(Float(precision=3))
    ndvi_std_dev = Column(Float(precision=3))

    # Comparison with baseline
    baseline_ndvi = Column(Float(precision=3))
    recovery_percentage = Column(Float(precision=2))

    # UC-08: Land use change detection
    land_use_classification = Column(String(50))
    classification_confidence = Column(Float(precision=2))  # 0-1
    classification_method = Column(String(50), default="rule_based")

    # Human activity detection
    human_activity_detected = Column(Boolean, default=False, index=True)
    activity_type = Column(String(50))
    activity_confidence = Column(String(20))

    # Observations
    notes = Column(Text)
    analyst_name = Column(String(100))

    # Relationships
    fire_event = relationship("FireEvent", back_populates="vegetation_monitoring")
    satellite_image = relationship(
        "SatelliteImage", back_populates="vegetation_monitoring"
    )
    land_use_change = relationship("LandUseChange", back_populates="monitoring_record")

    def __repr__(self):
        return f"<VegetationMonitoring(fire={self.fire_event_id}, month={self.month_number}, ndvi={self.ndvi_mean})>"
