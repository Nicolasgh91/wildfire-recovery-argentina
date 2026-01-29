"""
ForestGuard Services Module.

Exposes core services for satellite imagery analysis, report generation,
and cloud storage.

Services:
    - GEEService: Google Earth Engine access layer
    - VAEService: Vegetation Analysis Engine
    - ERSService: Evidence Reporting Service
    - StorageService: Cloudflare R2 storage
"""

from .gee_service import (
    GEEService,
    GEEError,
    GEEAuthenticationError,
    GEEImageNotFoundError,
    GEERateLimitError,
    ImageMetadata,
    NDVIResult,
    ImageResult,
)

from .vae_service import (
    VAEService,
    RecoveryStatus,
    LandUseChangeType,
    AnomalyType,
    Severity,
    RecoveryAnalysis,
    LandUseAnalysis,
    TemporalAnalysis,
    get_vae_service,
)

from .ers_service import (
    ERSService,
    ReportType,
    ReportStatus,
    ReportRequest,
    ImageEvidence,
    ReportResult,
)

from .storage_service import (
    StorageService,
    StorageError,
    StorageUploadError,
    StorageNotFoundError,
    UploadResult,
    StorageStats,
    get_storage_service,
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
