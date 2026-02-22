"""
ForestGuard Services Module.

Exposes core services for satellite imagery analysis, report generation,
and cloud storage.

Services:
    - GEEService: Google Earth Engine access layer
    - VAEService: Vegetation Analysis Engine
    - ERSService: Evidence Reporting Service
    - StorageService: Object storage (GCS/local/S3-compatible)
"""

from .ers_service import (
    ERSService,
    ImageEvidence,
    ReportRequest,
    ReportResult,
    ReportStatus,
    ReportType,
)
from .gee_service import (
    GEEAuthenticationError,
    GEEError,
    GEEImageNotFoundError,
    GEERateLimitError,
    GEEService,
    ImageMetadata,
    ImageResult,
    NDVIResult,
)
from .storage_service import (
    StorageError,
    StorageNotFoundError,
    StorageService,
    StorageStats,
    StorageUploadError,
    UploadResult,
    get_storage_service,
)
from .vae_service import (
    AnomalyType,
    LandUseAnalysis,
    LandUseChangeType,
    RecoveryAnalysis,
    RecoveryStatus,
    Severity,
    TemporalAnalysis,
    VAEService,
    get_vae_service,
)

__all__ = [
    # GEE Service
    "GEEService",
    "GEEError",
    "GEEAuthenticationError",
    "GEEImageNotFoundError",
    "GEERateLimitError",
    "ImageMetadata",
    "NDVIResult",
    "ImageResult",
    # VAE Service
    "VAEService",
    "RecoveryStatus",
    "LandUseChangeType",
    "AnomalyType",
    "Severity",
    "RecoveryAnalysis",
    "LandUseAnalysis",
    "TemporalAnalysis",
    "get_vae_service",
    # ERS Service
    "ERSService",
    "ReportType",
    "ReportStatus",
    "ReportRequest",
    "ImageEvidence",
    "ReportResult",
    # Storage Service
    "StorageService",
    "StorageError",
    "StorageUploadError",
    "StorageNotFoundError",
    "UploadResult",
    "StorageStats",
    "get_storage_service",
]
