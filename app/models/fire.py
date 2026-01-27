from sqlalchemy import Column, Integer, String, Boolean, DateTime, Numeric, Date, Time, ForeignKey, text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from geoalchemy2 import Geography
from sqlalchemy.ext.declarative import declarative_base

# Intentamos importar Base desde el lugar correcto
try:
    from app.db.base import Base
except ImportError:
    Base = declarative_base()

class FireEvent(Base):
    __tablename__ = "fire_events"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    
    # Geometría
    centroid = Column(Geography(geometry_type='POINT', srid=4326), nullable=False)
    perimeter = Column(Geography(geometry_type='POLYGON', srid=4326))
    
    # Tiempo
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    
    # Estadísticas
    total_detections = Column(Integer, default=1)
    avg_frp = Column(Numeric)
    max_frp = Column(Numeric)
    sum_frp = Column(Numeric)
    avg_confidence = Column(Numeric)
    estimated_area_hectares = Column(Numeric)
    
    # Metadatos
    province = Column(String)
    department = Column(String)
    is_significant = Column(Boolean, default=False)
    processing_error = Column(String)
    has_legal_analysis = Column(Boolean, default=False)
    
    # Auditoría
    created_at = Column(DateTime(timezone=True), server_default=text("now()"))
    updated_at = Column(DateTime(timezone=True), server_default=text("now()"))

    # Relaciones
    detections = relationship("FireDetection", back_populates="event")
    
    # --- LA LÍNEA QUE FALTABA (Relación con Áreas Protegidas) ---
    # Esto permite que SQLAlchemy cierre el círculo con region.py
    protected_area_intersections = relationship("FireProtectedAreaIntersection", back_populates="fire_event")


class FireDetection(Base):
    __tablename__ = "fire_detections"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    
    # Datos del sensor
    satellite = Column(String, nullable=False)
    instrument = Column(String, nullable=False)
    
    # Espaciotemporal
    detected_at = Column(DateTime(timezone=True), nullable=False)
    location = Column(Geography(geometry_type='POINT', srid=4326), nullable=False)
    latitude = Column(Numeric, nullable=False)
    longitude = Column(Numeric, nullable=False)
    
    # Temperaturas
    bt_mir_kelvin = Column(Numeric)
    bt_tir_kelvin = Column(Numeric)
    
    fire_radiative_power = Column(Numeric)
    confidence_raw = Column(String)
    confidence_normalized = Column(Integer)
    
    # Metadatos originales
    acquisition_date = Column(Date)
    acquisition_time = Column(Time)
    daynight = Column(String)
    
    # Estado de procesamiento
    is_processed = Column(Boolean, default=False)
    fire_event_id = Column(UUID(as_uuid=True), ForeignKey("fire_events.id"))
    
    # Relaciones
    event = relationship("FireEvent", back_populates="detections")