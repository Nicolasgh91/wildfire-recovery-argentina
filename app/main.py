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
from app.api.routes import (
    fires, certificates, audit,
    reports, monitoring, citizen, quality, analysis
)

# Setup logging
logger = setup_logging()


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


# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="API for legal oversight of wildfires in Argentina",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    dependencies=[Depends(verify_api_key), Depends(check_ip_rate_limit)]
)

app.include_router(
    certificates.router,
    prefix=f"{settings.API_V1_PREFIX}/certificates",
    tags=["certificates"],
    dependencies=[Depends(verify_api_key), Depends(check_ip_rate_limit)]
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
