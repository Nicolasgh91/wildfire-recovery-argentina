# =============================================================================
# WILDFIRE RECOVERIES IN ARGENTINA - SQLAlchemy ORM Models
# Versión: 3.0
# Fecha: 2025-01-24
# =============================================================================

"""
Modelos SQLAlchemy mapeados al schema PostgreSQL + PostGIS.

Organización:
- app/models/base.py          → Clase base y configuración
- app/models/fire.py          → FireDetection, FireEvent
- app/models/region.py        → ProtectedArea, FireProtectedAreaIntersection
- app/models/climate.py       → ClimateData, FireClimateAssociation
- app/models/evidence.py      → SatelliteImage, VegetationMonitoring
- app/models/audit.py         → LandUseAudit, LandCertificate
- app/models/citizen.py       → CitizenReport, LandUseChange
- app/models/quality.py       → DataSourceMetadata

Dependencias:
    pip install sqlalchemy geoalchemy2 psycopg2-binary
"""

# =============================================================================
# FILE: app/models/base.py
# =============================================================================

from datetime import datetime
from typing import Any
from uuid import uuid4

from geoalchemy2 import Geography
from sqlalchemy import Column, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import declared_attr

Base = declarative_base()


class TimestampMixin:
    """Mixin para columnas created_at y updated_at"""
    
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    
    updated_at = Column(
        DateTime(timezone=True),
        nullable=True,
        onupdate=func.now()
    )


class UUIDMixin:
    """Mixin para primary key UUID"""
    
    @declared_attr
    def id(cls):
        return Column(
            UUID(as_uuid=True),
            primary_key=True,
            default=uuid4,
            nullable=False
        )


