"""
SQLAlchemy Models para ForestGuard
Define la estructura de las tablas principales en PostgreSQL/Supabase

Tabla fire_detections: Puntos individuales detectados por NASA FIRMS
Tabla fire_events: Eventos agrupados por clustering DBSCAN
Tabla recovery_metrics: Análisis temporal de recuperación (NDVI)
Tabla destruction_reports: Análisis de cambios de uso de suelo
"""

from datetime import datetime
from typing import Optional

from geoalchemy2 import Geometry
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

# Base para todos los modelos
Base = declarative_base()


class FireDetection(Base):
    """
    Representa un punto individual de detección de fuego detectado por NASA FIRMS.

    Cada punto incluye coordenadas geográficas exactas, timestamp de detección,
    confianza del sensor, y potencia radiativa del fuego. Estos puntos son agrupados
    posteriormente mediante clustering DBSCAN en eventos discretos.

    Una ubicación puede tener múltiples detecciones en el tiempo, representando
    la evolución espacial y temporal del fuego mientras avanza.
    """

    __tablename__ = "fire_detections"

    # Identificador único
    id = Column(String(36), primary_key=True, comment="UUID único de la detección")

    # Ubicación geográfica - PostGIS Geometry permite queries espaciales eficientes
    # El SRID 4326 es WGS84 (lat/lon estándar global)
    latitude = Column(Float, nullable=False, comment="Latitud de la detección (WGS84)")
    longitude = Column(
        Float, nullable=False, comment="Longitud de la detección (WGS84)"
    )
    geometry = Column(
        Geometry("POINT", srid=4326),
        nullable=False,
        comment="Punto geográfico para queries PostGIS",
    )

    # Timestamp cuando fue detectado
    detected_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        comment="Fecha/hora UTC de detección",
    )

    # Atributos de detección de NASA FIRMS
    confidence = Column(
        Float, nullable=False, comment="Confianza de detección (0-100%)"
    )
    frp = Column(Float, nullable=True, comment="Fire Radiative Power en MW")
    satellite = Column(
        String(50), nullable=False, comment="Satélite que detectó (VIIRS, MODIS, etc)"
    )

    # Ubicación administrativa
    province = Column(
        String(100), nullable=False, comment="Provincia de Argentina donde ocurrió"
    )
    department = Column(
        String(100), nullable=True, comment="Departamento dentro de la provincia"
    )

    # Metadatos
    created_at = Column(
        DateTime, default=datetime.utcnow, comment="Cuando fue insertado en BD"
    )
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relación con fire_events (un fire_event puede tener muchas detecciones)
    fire_event_id = Column(
        String(36),
        ForeignKey("fire_events.id"),
        nullable=True,
        comment="ID del evento si fue agrupado por clustering",
    )
    fire_event = relationship("FireEvent", back_populates="detections")

    def __repr__(self):
        return f"<FireDetection(id={self.id}, lat={self.latitude}, lon={self.longitude}, confidence={self.confidence})>"


class FireEvent(Base):
    """
    Representa un evento de fuego agrupado por clustering DBSCAN.

    Después que DBSCAN agrupa las detecciones individuales en clusters espaciales,
    se crea un FireEvent que representa el incendio como una entidad única.
    Incluye perímetro del incendio, estadísticas agregadas, y duración total.

    Esta es la "vista de usuario" de un incendio - lo que aparecería en un mapa
    como un polígono único en lugar de puntos dispersos.
    """

    __tablename__ = "fire_events"

    # Identificador único
    id = Column(String(36), primary_key=True, comment="UUID único del evento")

    # Geometría - El perímetro es un polígono que envuelve todas las detecciones
    # Puede ser un simple convex hull o un boundary más complejo
    geometry = Column(
        Geometry("POLYGON", srid=4326),
        nullable=False,
        comment="Perímetro del incendio (polígono)",
    )

    # Temporal
    started_at = Column(
        DateTime, nullable=False, comment="Primer punto de detección del incendio"
    )
    ended_at = Column(
        DateTime,
        nullable=True,
        comment="Último punto detectado (puede estar aún activo si NULL)",
    )
    duration_hours = Column(Integer, nullable=True, comment="Duración total en horas")

    # Estadísticas agregadas
    affected_area_ha = Column(
        Float, nullable=False, comment="Área afectada en hectáreas"
    )
    avg_frp = Column(Float, nullable=True, comment="Potencia radiativa promedio en MW")
    max_frp = Column(Float, nullable=True, comment="Potencia radiativa máxima en MW")
    total_detections = Column(
        Integer, nullable=False, comment="Cantidad de puntos en el cluster"
    )

    # Ubicación administrativa
    province = Column(String(100), nullable=False, comment="Provincia principal")
    department = Column(String(100), nullable=True, comment="Departamento principal")

    # Estado del incendio
    status = Column(
        String(50), default="active", comment="Estado: active, contained, extinguished"
    )
    severity = Column(
        String(50), nullable=True, comment="Severidad: low, medium, high, critical"
    )

    # Relaciones con áreas protegidas (si aplica)
    in_protected_area = Column(
        Boolean, default=False, comment="¿Está en área protegida?"
    )
    protected_area_name = Column(
        String(200), nullable=True, comment="Nombre del área protegida si aplica"
    )

    # Metadatos
    created_at = Column(
        DateTime, default=datetime.utcnow, comment="Cuando fue creado el evento"
    )
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relaciones
    detections = relationship(
        "FireDetection", back_populates="fire_event", cascade="all, delete-orphan"
    )
    recovery_metrics = relationship(
        "RecoveryMetric", back_populates="fire_event", cascade="all, delete-orphan"
    )
    destruction_report = relationship(
        "DestructionReport",
        back_populates="fire_event",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<FireEvent(id={self.id}, area={self.affected_area_ha}ha, status={self.status})>"


class RecoveryMetric(Base):
    """
    Representa medición temporal de recuperación post-incendio.

    Después que un incendio ocurre, se monitorea la recuperación de vegetación
    mediante índices NDVI (Normalized Difference Vegetation Index) de Google Earth Engine.
    Se toman múltiples mediciones en diferentes momentos (3, 6, 12 meses post-incendio)
    para entender la velocidad y completitud de recuperación.

    NDVI ronda de -1 (agua) a +1 (vegetación densa). Vegetación quemada tiene NDVI bajo.
    Si NDVI sube con el tiempo, la vegetación está recuperándose.
    """

    __tablename__ = "recovery_metrics"

    # Identificador único
    id = Column(String(36), primary_key=True, comment="UUID único de la métrica")

    # Relación con el evento de fuego
    fire_event_id = Column(String(36), ForeignKey("fire_events.id"), nullable=False)
    fire_event = relationship("FireEvent", back_populates="recovery_metrics")

    # Temporal
    measurement_date = Column(DateTime, nullable=False, comment="Fecha de la medición")
    months_after_fire = Column(
        Integer, nullable=False, comment="Meses transcurridos desde el inicio del fuego"
    )

    # Índices de vegetación - Estos números muestran salud de vegetación
    ndvi_pre_fire = Column(
        Float, nullable=True, comment="NDVI promedio antes del incendio"
    )
    ndvi_post_fire = Column(
        Float, nullable=True, comment="NDVI inmediatamente después del incendio"
    )
    ndvi_current = Column(
        Float, nullable=False, comment="NDVI actual en fecha de medición"
    )

    # Análisis de recuperación
    recovery_percentage = Column(
        Float, nullable=False, comment="Porcentaje de recuperación (0-100%)"
    )
    recovery_status = Column(
        String(50),
        nullable=False,
        comment="Estado: recovering, stable, degraded, stalled",
    )

    # Confianza del análisis
    confidence = Column(Float, nullable=False, comment="Confianza de la medición (0-1)")

    # Datos crudos para debugging
    gee_data = Column(
        JSON, nullable=True, comment="Datos raw de Google Earth Engine para debugging"
    )

    # Metadatos
    created_at = Column(DateTime, default=datetime.utcnow)
    analysis_notes = Column(
        Text, nullable=True, comment="Notas adicionales del análisis"
    )

    def __repr__(self):
        return f"<RecoveryMetric(fire_id={self.fire_event_id}, months={self.months_after_fire}, recovery={self.recovery_percentage}%)>"


class DestructionReport(Base):
    """
    Representa análisis de destrucción y cambio de uso de suelo post-incendio.

    Después de un incendio, el suelo quemado es vulnerable a cambios de uso.
    Este reporte analiza imágenes multitemporales de Sentinel-2 para detectar:
    - Reforestación natural o plantada
    - Conversión a agricultura
    - Urbanización
    - Degradación del suelo
    - Permanencia como bosque sin cambio

    La Ley 26.815 de Argentina establece prohibiciones de 60 años para cambios
    de uso de suelo en bosques nativos y áreas protegidas. Este reporte es
    evidencia de cumplimiento o violación de la ley.
    """

    __tablename__ = "destruction_reports"

    # Identificador único
    id = Column(String(36), primary_key=True, comment="UUID único del reporte")

    # Relación con el evento de fuego (uno a uno - un reporte por evento)
    fire_event_id = Column(
        String(36), ForeignKey("fire_events.id"), nullable=False, unique=True
    )
    fire_event = relationship("FireEvent", back_populates="destruction_report")

    # Temporal - Análisis a diferentes momentos post-incendio
    analysis_date = Column(DateTime, nullable=False, comment="Fecha del análisis")
    months_after_fire = Column(Integer, nullable=False, comment="Meses desde incendio")

    # Clasificación de cambio de uso detectado
    primary_land_use = Column(
        String(100),
        nullable=False,
        comment="Uso de suelo detectado: forest, agriculture, urban, degraded, water",
    )
    confidence = Column(
        Float, nullable=False, comment="Confianza de la clasificación (0-1)"
    )

    # Áreas detectadas para cada categoría
    forest_area_ha = Column(
        Float, default=0, comment="Área recalificada como bosque (hectáreas)"
    )
    agriculture_area_ha = Column(
        Float, default=0, comment="Área convertida a agricultura (hectáreas)"
    )
    urban_area_ha = Column(Float, default=0, comment="Área urbanizada (hectáreas)")
    degraded_area_ha = Column(
        Float, default=0, comment="Área degradada sin cambio de uso (hectáreas)"
    )
    water_area_ha = Column(
        Float, default=0, comment="Área con agua/cuerpos de agua (hectáreas)"
    )

    # Análisis legal
    legal_status = Column(
        String(50),
        nullable=False,
        comment="Estado legal: compliant, violation, pending, unknown",
    )
    legal_notes = Column(
        Text, nullable=True, comment="Notas sobre implicaciones Ley 26.815"
    )

    # Archivo del reporte (URL en GCS)
    report_pdf_url = Column(
        String(500), nullable=True, comment="URL a reporte PDF en Google Cloud Storage"
    )
    report_generated_at = Column(
        DateTime, nullable=True, comment="Cuando fue generado el PDF"
    )

    # Evidencia geoespacial
    evidence_geometry = Column(
        Geometry("MULTIPOLYGON", srid=4326),
        nullable=True,
        comment="Polígonos de áreas detectadas",
    )

    # Metadatos
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    analysis_notes = Column(Text, nullable=True, comment="Notas técnicas del análisis")

    def __repr__(self):
        return f"<DestructionReport(fire_id={self.fire_event_id}, primary_use={self.primary_land_use}, legal={self.legal_status})>"


# Índices adicionales para performance (se crearían en migraciones Alembic)
# CREATE INDEX idx_fire_detections_geometry ON fire_detections USING GIST(geometry);
# CREATE INDEX idx_fire_detections_detected_at ON fire_detections(detected_at);
# CREATE INDEX idx_fire_detections_province ON fire_detections(province);
# CREATE INDEX idx_fire_events_geometry ON fire_events USING GIST(geometry);
# CREATE INDEX idx_fire_events_started_at ON fire_events(started_at);
# CREATE INDEX idx_fire_events_status ON fire_events(status);
# CREATE INDEX idx_recovery_metrics_fire_event_id ON recovery_metrics(fire_event_id);
# CREATE INDEX idx_destruction_reports_fire_event_id ON destruction_reports(fire_event_id);
