from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from app.core.config import settings
from app.core.logging import setup_logging
from app.api.routes import fires, certificates, audit #, reports, monitoring, citizen

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

# Include routers
app.include_router(
    fires.router,
    prefix=f"{settings.API_V1_PREFIX}/fires",
    tags=["fires"]
)
# COMENTADO POR MVP, faltan actualizaciones en otros módulos

app.include_router(
    audit.router,
    prefix=f"{settings.API_V1_PREFIX}/audit",
    tags=["audit"]
)
"""
app.include_router(
    reports.router,
    prefix=f"{settings.API_V1_PREFIX}/reports",
    tags=["reports"]
)
"""
app.include_router(
    certificates.router,
    prefix=f"{settings.API_V1_PREFIX}/certificates",
    tags=["certificates"]
)
"""
app.include_router(
    monitoring.router,
    prefix=f"{settings.API_V1_PREFIX}/monitoring",
    tags=["monitoring"]
)

app.include_router(
    citizen.router,
    prefix=f"{settings.API_V1_PREFIX}/citizen",
    tags=["citizen"]
)
"""

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT
    }


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API info"""
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs": "/docs",
        "health": "/health"
    }