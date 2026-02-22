"""
Importar todos los modelos en un solo lugar para facilitar el uso.

Uso:
    from app.models import FireEvent, ProtectedArea, LandCertificate
"""

from .alerts import ParkAlert
from .audit import LandCertificate, LandUseAudit
from .base import Base
from .certificate import BurnCertificate
from .citizen import CitizenReport, LandUseChange
from .climate import ClimateData, FireClimateAssociation
from .clustering import ClusteringVersion, EpisodeMerger
from .episode import FireEpisode, FireEpisodeEvent
from .evidence import SatelliteImage, VegetationMonitoring
from .exploration import (
    HdGenerationJob,
    InvestigationAsset,
    InvestigationItem,
    InvestigationShare,
    UserInvestigation,
)
from .fire import FireDetection, FireEvent
from .payment import CreditTransaction, PaymentRequest, PaymentWebhookLog, UserCredits
from .quality import DataSourceMetadata
from .region import FireProtectedAreaIntersection, ProtectedArea
from .system_audit import AuditEvent
from .visitor import Shelter, VisitorLog, VisitorLogCompanion, VisitorLogRevision

__all__ = [
    # Base
    "Base",
    # Fire models
    "FireDetection",
    "FireEvent",
    "FireEpisode",
    "FireEpisodeEvent",
    "ClusteringVersion",
    "EpisodeMerger",
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
    "AuditEvent",
    # Alerts models
    "ParkAlert",
    # Citizen models
    "CitizenReport",
    "LandUseChange",
    # Quality models
    "DataSourceMetadata",
    # Certificate models
    "BurnCertificate",
    # Visitor models
    "Shelter",
    "VisitorLog",
    "VisitorLogCompanion",
    "VisitorLogRevision",
    # Payment models
    "PaymentRequest",
    "PaymentWebhookLog",
    "UserCredits",
    "CreditTransaction",
    # Exploration models
    "UserInvestigation",
    "InvestigationItem",
    "InvestigationAsset",
    "InvestigationShare",
    "HdGenerationJob",
]
