import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import (
    alerts,
    auth,
    certificates,
    citizen,
    episodes,
    health,
    historical,
    monitoring,
    reports,
    visitor_logs,
    workers,
    tasks
)
from app.api.v1 import (
    analysis,
    audit,
    contact,
    explorations,
    fire_events,
    fires,
    imagery,
    payments,
    quality,
    webhooks,
)
from app.core.config import settings
from app.core.errors import register_exception_handlers
from app.core.feature_flags import require_feature
from app.core.logging import setup_logging
from app.core.middleware import (
    DeprecationMiddleware,
    LatencyMonitorMiddleware,
    RequestIdMiddleware,
)
from app.core.rate_limiter import check_ip_rate_limit
from app.core.security import verify_api_key

# Setup logging
logger = setup_logging()


# =============================================================================
# OpenAPI Tags Metadata
# =============================================================================
tags_metadata = [
    {
        "name": "fires",
        "description": "**Fire Events** - List and retrieve wildfire events detected by satellite. Supports filtering by date, province, and significance. / *Eventos de incendio detectados por satélite.*",
    },
    {
        "name": "explorations",
        "description": "**Explorations** - Wizard-friendly endpoints to explore fire event evolution without generating imagery. / *Exploracion de incendios para usuarios no tecnicos.*",
    },
    {
        "name": "episodes",
        "description": "**Fire Episodes (UC-17)** - Macro grouping of fire events for GEE optimization. / *Agrupación macro de incendios para optimizar requests a GEE.*",
    },
    {
        "name": "stats",
        "description": "**Statistics** - Aggregate fire statistics and metrics. / *Estadísticas agregadas de incendios.*",
    },
    {
        "name": "audit",
        "description": "**Land Use Audit (UC-01)** - Verify legal restrictions on land due to previous fires under Law 26.815 Art. 22 bis. **Requires API key.** / *Auditoría de restricciones legales por incendios previos.*",
    },
    {
        "name": "certificates",
        "description": "**Legal Certificates (UC-07)** - Issue and verify digital certificates for land legal status. **Requires API key.** / *Certificados digitales verificables del estado legal del terreno.*",
    },
    {
        "name": "monitoring",
        "description": "**Vegetation Recovery (UC-06)** - Track NDVI-based vegetation recovery in burnt areas over 36 months. / *Monitoreo de recuperación de vegetación post-incendio.*",
    },
    {
        "name": "reports",
        "description": "**Reports (UC-02, UC-11)** - Generate judicial forensic reports and historical fire reports with satellite evidence. **Requires API key.** / *Reportes judiciales e históricos con evidencia satelital.*",
    },
    {
        "name": "citizen",
        "description": "**Citizen Reports (UC-09)** - Submit citizen reports of suspicious activity in burnt areas. / *Denuncias ciudadanas de actividad sospechosa.*",
    },
    {
        "name": "contact",
        "description": "**Contact (UC-F01)** - Public contact form with optional attachments. / *Formulario de contacto pÃºblico con adjuntos opcionales.*",
    },
    {
        "name": "quality",
        "description": "**Data Quality (UC-10)** - Reliability metrics and data source transparency for forensic use. / *Métricas de confiabilidad para uso forense.*",
    },
    {
        "name": "analysis",
        "description": "**Analysis (UC-03, UC-05)** - Fire recurrence patterns and historical trend analysis. / *Análisis de patrones de recurrencia y tendencias históricas.*",
    },
    {
        "name": "historical",
        "description": "**Historical Data (UC-11)** - Access historical fire records with satellite imagery. **Requires API key.** / *Datos históricos de incendios con imágenes satelitales.*",
    },
    {
        "name": "imagery",
        "description": "**Imagery (UC-F08)** - Manual refresh of carousel thumbnails. **Admin only.** / *RegeneraciÃ³n manual de thumbnails del carrusel.*",
    },
    {
        "name": "workers",
        "description": "**Workers (UC-08)** - Trigger background land-use change detection for post-fire monitoring. / *Tareas de detección de cambio de uso del suelo post-incendio.*",
    },
    {
        "name": "alerts",
        "description": "**Alerts (UC-04)** - Park carrying-capacity alerts and preventative notifications. / *Alertas de capacidad de carga en parques.*",
    },
    {
        "name": "visitor-logs",
        "description": "**Visitor Logs (UC-12)** - Offline-first visitor registration records. / *Registro de visitantes en refugios.*",
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
## ForestGuard API

REST API for **legal oversight of wildfires** in protected areas of Argentina, implementing Law 26.815 (Fire Management Law).

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

# Request ID Tracing (ROB-002)
app.add_middleware(RequestIdMiddleware)

# Register global exception handlers
register_exception_handlers(app)

# Include routers
# Auth - no API key required
app.include_router(auth.router, prefix=f"{settings.API_V1_PREFIX}/auth", tags=["auth"])

app.include_router(
    fires.router, prefix=f"{settings.API_V1_PREFIX}/fires", tags=["fires"]
)

app.include_router(
    fire_events.router, prefix=f"{settings.API_V1_PREFIX}/fire-events", tags=["fires"]
)

app.include_router(
    explorations.router,
    prefix=f"{settings.API_V1_PREFIX}/explorations",
    tags=["explorations"],
)

app.include_router(
    fires.filters_router, prefix=f"{settings.API_V1_PREFIX}", tags=["fires"]
)

app.include_router(
    episodes.router, prefix=f"{settings.API_V1_PREFIX}/fire-episodes", tags=["episodes"]
)

app.include_router(
    audit.router,
    prefix=f"{settings.API_V1_PREFIX}/audit",
    tags=["audit"],
    dependencies=[Depends(verify_api_key)],
)

app.include_router(
    certificates.router,
    prefix=f"{settings.API_V1_PREFIX}/certificates",
    tags=["certificates"],
    dependencies=[Depends(require_feature("certificates")), Depends(verify_api_key)],
)

# UC-06: Vegetation Recovery Monitoring
app.include_router(
    monitoring.router,
    prefix=f"{settings.API_V1_PREFIX}/monitoring",
    tags=["monitoring"],
)

# UC-02, UC-11: Reports (Judicial, Historical)
app.include_router(
    reports.router,
    prefix=f"{settings.API_V1_PREFIX}/reports",
    tags=["reports"],
    dependencies=[Depends(verify_api_key)],
)

# UC-13: Payments (MercadoPago)
app.include_router(
    payments.router,
    prefix=f"{settings.API_V1_PREFIX}/payments",
    tags=["payments"],
)

# Webhooks (MercadoPago)
app.include_router(
    webhooks.router,
    prefix=f"{settings.API_V1_PREFIX}",
    tags=["webhooks"],
)

# UC-09: Citizen Reports (no API key required for submission)
app.include_router(
    citizen.router, prefix=f"{settings.API_V1_PREFIX}/citizen", tags=["citizen"]
)

# UC-F01: Contact and support (public)
app.include_router(contact.router, prefix=f"{settings.API_V1_PREFIX}", tags=["contact"])

# UC-10: Data Quality Metrics
app.include_router(
    quality.router, prefix=f"{settings.API_V1_PREFIX}/quality", tags=["quality"]
)

# UC-03, UC-05: Analysis (Recurrence, Trends)
app.include_router(
    analysis.router, prefix=f"{settings.API_V1_PREFIX}/analysis", tags=["analysis"]
)

# UC-04: Park capacity alerts
app.include_router(
    alerts.router,
    prefix=f"{settings.API_V1_PREFIX}/alerts",
    tags=["alerts"],
    dependencies=[Depends(verify_api_key)],
)

# UC-12: Visitor logs and shelters (UC-F07)
app.include_router(
    visitor_logs.router,
    prefix=f"{settings.API_V1_PREFIX}",
    tags=["visitor-logs"],
    dependencies=[Depends(require_feature("refuges"))],
)

# UC-12: Historical Reports (Legacy reports with satellite imagery)
app.include_router(
    historical.router,
    prefix=f"{settings.API_V1_PREFIX}/historical",
    tags=["historical"],
    dependencies=[Depends(verify_api_key)],
)

# UC-F08: Manual imagery refresh (admin-only)
app.include_router(
    imagery.router, prefix=f"{settings.API_V1_PREFIX}/imagery", tags=["imagery"]
)

# UC-08: Land Use Change Detection (worker-triggered)
app.include_router(
    workers.router,
    prefix=f"{settings.API_V1_PREFIX}/workers",
    tags=["workers"],
    dependencies=[Depends(verify_api_key)],
)

# Maintenance Tasks (Celery)
app.include_router(
    tasks.router, # This is the new generalized tasks router
    prefix=f"{settings.API_V1_PREFIX}/tasks",
    tags=["tasks"],
    dependencies=[Depends(verify_api_key)],
)

# Health checks - detailed service status (ROB-003)
app.include_router(
    health.router, prefix=f"{settings.API_V1_PREFIX}/health", tags=["health"]
)


# Health check endpoint
@app.get(
    "/health",
    summary="Health check",
    description="""
    Returns service health metadata for monitoring and uptime checks.
    
    ---
    Devuelve metadatos de salud del servicio para monitoreo y checks de uptime.
    """,
)
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
    }


# Root endpoint
@app.get(
    "/",
    summary="API root",
    description="""
    Returns basic API metadata and links to documentation and health endpoints.
    
    ---
    Devuelve metadatos básicos de la API y enlaces a documentación y health.
    """,
)
async def root():
    """Root endpoint with API info"""
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs": "/docs",
        "health": "/health",
    }
