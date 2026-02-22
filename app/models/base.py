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

from app.db.base import Base, TimestampMixin, UUIDMixin

__all__ = ["Base", "TimestampMixin", "UUIDMixin"]
