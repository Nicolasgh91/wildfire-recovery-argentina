"""
Importar todos los modelos en un solo lugar para facilitar el uso.

Uso:
    from app.models import FireEvent, ProtectedArea, LandCertificate
"""

from .audit import LandCertificate, LandUseAudit
from .base import Base
from .citizen import CitizenReport, LandUseChange
from .climate import ClimateData, FireClimateAssociation
from .evidence import SatelliteImage, VegetationMonitoring
from .fire import FireDetection, FireEvent
from .quality import DataSourceMetadata
from .region import FireProtectedAreaIntersection, ProtectedArea
from .certificate import BurnCertificate

__all__ = [
    # Base
    "Base",
    
    # Fire models
    "FireDetection",
    "FireEvent",
    
    # Region models
    "ProtectedArea",
    "FireProtectedAreaIntersection",
    
    # Climate models
    "ClimateData",
    "FireClimateAssociation",
    
    # Evidence models
    "SatelliteImage",
    "VegetationMonitoring",
    
    # Audit models
    "LandUseAudit",
    "LandCertificate",
    
    # Citizen models
    "CitizenReport",
    "LandUseChange",
    
    # Quality models
    "DataSourceMetadata",

    # Certificate models
    "BurnCertificate",

]