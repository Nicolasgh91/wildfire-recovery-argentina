from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from app.core.config import settings
from app.core.logging import setup_logging
from app.core.errors import register_exception_handlers
from app.core.security import verify_api_key
from app.core.rate_limiter import check_ip_rate_limit
from app.core.middleware import LatencyMonitorMiddleware, DeprecationMiddleware
from app.api.routes import (
    fires, certificates, audit,
    reports, monitoring, citizen, quality, analysis, historical
)

# Setup logging
logger = setup_logging()


# =============================================================================
# OpenAPI Tags Metadata
# =============================================================================
tags_metadata = [
    {
        "name": "fires",
        "description": "🔥 **Fire Events** - List and retrieve wildfire events detected by satellite. Supports filtering by date, province, and significance. / *Eventos de incendio detectados por satélite.*",
    },
    {
        "name": "stats",
        "description": "📊 **Statistics** - Aggregate fire statistics and metrics. / *Estadísticas agregadas de incendios.*",
    },
    {
        "name": "audit",
        "description": "📋 **Land Use Audit (UC-01)** - Verify legal restrictions on land due to previous fires under Law 26.815 Art. 22 bis. **Requires API key.** / *Auditoría de restricciones legales por incendios previos.*",
    },
    {
        "name": "certificates",
        "description": "📜 **Legal Certificates (UC-07)** - Issue and verify digital certificates for land legal status. **Requires API key.** / *Certificados digitales verificables del estado legal del terreno.*",
    },
    {
        "name": "monitoring",
        "description": "🌱 **Vegetation Recovery (UC-06)** - Track NDVI-based vegetation recovery in burnt areas over 36 months. / *Monitoreo de recuperación de vegetación post-incendio.*",
    },
    {
        "name": "reports",
        "description": "📑 **Reports (UC-02, UC-11)** - Generate judicial forensic reports and historical fire reports with satellite evidence. **Requires API key.** / *Reportes judiciales e históricos con evidencia satelital.*",
    },
    {
        "name": "citizen",
        "description": "🧑‍🤝‍🧑 **Citizen Reports (UC-09)** - Submit citizen reports of suspicious activity in burnt areas. / *Denuncias ciudadanas de actividad sospechosa.*",
    },
    {
        "name": "quality",
        "description": "🔬 **Data Quality (UC-10)** - Reliability metrics and data source transparency for forensic use. / *Métricas de confiabilidad para uso forense.*",
    },
    {
        "name": "analysis",
        "description": "📈 **Analysis (UC-03, UC-05)** - Fire recurrence patterns and historical trend analysis. / *Análisis de patrones de recurrencia y tendencias históricas.*",
    },
    {
        "name": "historical",
        "description": "🗂️ **Historical Data (UC-11)** - Access historical fire records with satellite imagery. **Requires API key.** / *Datos históricos de incendios con imágenes satelitales.*",
    },
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")


# Create FastAPI app with comprehensive OpenAPI metadata
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="""
## ForestGuard API 🌲🔥

REST API for **legal oversight of wildfires** in protected areas of Argentina, implementing Law 26.815 (Fire Management Law).

### 🎯 Key Use Cases

| UC | Name | Description |
|----|------|-------------|
| UC-01 | Land Use Audit | Verify legal restrictions due to fires |
| UC-07 | Legal Certification | Issue verifiable digital certificates |
| UC-06 | Vegetation Recovery | NDVI monitoring of burnt areas |
| UC-10 | Data Quality | Reliability metrics for forensics |
| UC-11 | Historical Reports | PDFs of fires in protected areas |

### 🔐 Authentication

Protected endpoints require the `X-API-Key` header:
```
X-API-Key: your-api-key-here
```

Endpoints marked with 🔒 in their tag descriptions require authentication.

### 📊 Rate Limits

- **Public endpoints**: 100 requests/minute per IP
- **Authenticated endpoints**: 10 requests/day per IP (sensitive operations)

### 🌐 Bilingual Support

All responses include both English and Spanish content where applicable.

---

*Data sources: NASA FIRMS (VIIRS/MODIS), Sentinel-2, Google Earth Engine*
    """,
    openapi_tags=tags_metadata,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    contact={
        "name": "ForestGuard Team",
        "url": "https://github.com/forestguard/api",
        "email": "contact@forestguard.ar",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Deprecation Headers (RFC 8594)
app.add_middleware(DeprecationMiddleware)

# Latency Monitoring (SLO Check)
app.add_middleware(LatencyMonitorMiddleware)

# Register global exception handlers
register_exception_handlers(app)

# Include routers
app.include_router(
    fires.router,
    prefix=f"{settings.API_V1_PREFIX}/fires",
    tags=["fires"]
)

app.include_router(
    audit.router,
    prefix=f"{settings.API_V1_PREFIX}/audit",
    tags=["audit"],
    dependencies=[Depends(verify_api_key)]
)

app.include_router(
    certificates.router,
    prefix=f"{settings.API_V1_PREFIX}/certificates",
    tags=["certificates"],
    dependencies=[Depends(verify_api_key)]
)

# UC-06: Vegetation Recovery Monitoring
app.include_router(
    monitoring.router,
    prefix=f"{settings.API_V1_PREFIX}/monitoring",
    tags=["monitoring"]
)

# UC-02, UC-11: Reports (Judicial, Historical)
app.include_router(
    reports.router,
    prefix=f"{settings.API_V1_PREFIX}/reports",
    tags=["reports"],
    dependencies=[Depends(verify_api_key)]
)

# UC-09: Citizen Reports (no API key required for submission)
app.include_router(
    citizen.router,
    prefix=f"{settings.API_V1_PREFIX}/citizen",
    tags=["citizen"]
)

# UC-10: Data Quality Metrics
app.include_router(
    quality.router,
    prefix=f"{settings.API_V1_PREFIX}/quality",
    tags=["quality"]
)

# UC-03, UC-05: Analysis (Recurrence, Trends)
app.include_router(
    analysis.router,
    prefix=f"{settings.API_V1_PREFIX}/analysis",
    tags=["analysis"]
)

# UC-12: Historical Reports (Legacy reports with satellite imagery)
app.include_router(
    historical.router,
    prefix=f"{settings.API_V1_PREFIX}/historical",
    tags=["historical"],
    dependencies=[Depends(verify_api_key)]
)

# Health check endpoint
@app.get(
    "/health",
    summary="Health check",
    description="""
    Returns service health metadata for monitoring and uptime checks.
    
    ---
    Devuelve metadatos de salud del servicio para monitoreo y checks de uptime.
    """
)
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT
    }


# Root endpoint
@app.get(
    "/",
    summary="API root",
    description="""
    Returns basic API metadata and links to documentation and health endpoints.
    
    ---
    Devuelve metadatos básicos de la API y enlaces a documentación y health.
    """
)
async def root():
    """Root endpoint with API info"""
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs": "/docs",
        "health": "/health"
    }
