"""
Health check endpoints for ForestGuard API.

Provides:
- /detailed - Full health check with all services
- /ready - Readiness probe (DB connectivity)
- /live - Liveness probe (service alive)
- /db - Database connectivity check
- /celery - Celery broker check
- /gee - GEE credentials check
"""
import time
from datetime import datetime
from typing import Any, Dict, Literal, Optional

import redis
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api import deps
from app.core.celery_runtime import resolve_celery_broker_url

router = APIRouter(tags=["health"])


class ServiceHealth(BaseModel):
    """Health status of an individual service."""

    status: Literal["healthy", "degraded", "unhealthy"]
    latency_ms: Optional[float] = None
    message: Optional[str] = None


class DetailedHealthResponse(BaseModel):
    """Comprehensive health check response."""

    status: Literal["healthy", "degraded", "unhealthy"]
    version: str
    environment: str
    timestamp: datetime
    services: Dict[str, ServiceHealth]

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "version": "1.0.0",
                "environment": "production",
                "timestamp": "2026-02-08T14:30:00Z",
                "services": {
                    "database": {"status": "healthy", "latency_ms": 5.2},
                    "redis": {"status": "healthy", "latency_ms": 1.1},
                    "storage": {"status": "healthy", "latency_ms": 12.5},
                },
            }
        }


async def check_database(db: Session) -> ServiceHealth:
    """Check database connectivity and latency."""
    import time

    try:
        start = time.perf_counter()
        db.execute(text("SELECT 1"))
        latency = (time.perf_counter() - start) * 1000
        return ServiceHealth(status="healthy", latency_ms=round(latency, 2))
    except Exception as e:
        return ServiceHealth(status="unhealthy", message=str(e)[:100])


async def check_redis() -> ServiceHealth:
    """Check Redis connectivity."""
    try:
        start = time.perf_counter()
        broker_url = resolve_celery_broker_url()
        client = redis.from_url(broker_url, socket_timeout=2)
        client.ping()
        latency = (time.perf_counter() - start) * 1000
        return ServiceHealth(status="healthy", latency_ms=round(latency, 2))
    except Exception as e:
        return ServiceHealth(
            status="degraded", message=f"Redis unavailable: {str(e)[:50]}"
        )


async def check_storage() -> ServiceHealth:
    """Check object storage connectivity."""
    import time

    try:
        from app.core.config import settings

        if settings.STORAGE_BACKEND == "local":
            import os

            start = time.perf_counter()
            exists = os.path.exists(settings.STORAGE_LOCAL_PATH)
            latency = (time.perf_counter() - start) * 1000
            if exists:
                return ServiceHealth(
                    status="healthy", latency_ms=round(latency, 2)
                )
            return ServiceHealth(
                status="degraded", message="Local storage path not found"
            )
        else:
            # GCS check would go here
            return ServiceHealth(status="healthy", message="GCS configured")
    except Exception as e:
        return ServiceHealth(status="degraded", message=str(e)[:50])


@router.get(
    "/detailed",
    response_model=DetailedHealthResponse,
    summary="Detailed health check",
    description="""
    Returns comprehensive health status including all dependent services.
    
    **Services checked:**
    - Database (PostgreSQL)
    - Redis (Celery broker)
    - Object Storage (GCS/Local)
    
    **Status levels:**
    - `healthy`: All services operational
    - `degraded`: Non-critical services unavailable
    - `unhealthy`: Critical services down
    """,
)
async def detailed_health_check(
    db: Session = Depends(deps.get_db),
) -> DetailedHealthResponse:
    """Perform comprehensive health check of all services."""
    from app.core.config import settings

    # Check all services
    db_health = await check_database(db)
    redis_health = await check_redis()
    storage_health = await check_storage()

    services = {
        "database": db_health,
        "redis": redis_health,
        "storage": storage_health,
    }

    # Determine overall status
    statuses = [s.status for s in services.values()]
    if "unhealthy" in statuses:
        overall = "unhealthy"
    elif "degraded" in statuses:
        overall = "degraded"
    else:
        overall = "healthy"

    return DetailedHealthResponse(
        status=overall,
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        timestamp=datetime.utcnow(),
        services=services,
    )


@router.get(
    "/ready",
    summary="Readiness probe",
    description="Quick check if the service is ready to accept traffic.",
)
async def readiness_probe(
    db: Session = Depends(deps.get_db),
) -> Dict[str, Any]:
    """Kubernetes-style readiness probe."""
    try:
        db.execute(text("SELECT 1"))
        return {"ready": True}
    except Exception:
        return {"ready": False}


@router.get(
    "/live",
    summary="Liveness probe",
    description="Quick check if the service is alive.",
)
async def liveness_probe() -> Dict[str, Any]:
    """Kubernetes-style liveness probe."""
    return {"alive": True, "timestamp": datetime.utcnow().isoformat()}


@router.get(
    "/db",
    summary="Database health check",
    description="Check database connectivity and latency.",
)
async def db_health_check(
    db: Session = Depends(deps.get_db),
) -> Dict[str, Any]:
    """Individual database health check endpoint."""
    result = await check_database(db)
    status_code = 200 if result.status == "healthy" else 503
    return JSONResponse(content=result.model_dump(), status_code=status_code)


@router.get(
    "/celery",
    summary="Celery health check",
    description="Check Celery broker (Redis) connectivity.",
)
async def celery_health_check() -> Dict[str, Any]:
    """Individual Celery/Redis health check endpoint."""
    result = await check_redis()
    status_code = 200 if result.status == "healthy" else 503
    return JSONResponse(content=result.model_dump(), status_code=status_code)


@router.get(
    "/gee",
    summary="GEE health check",
    description="Check Google Earth Engine credentials availability.",
)
async def gee_health_check() -> Dict[str, Any]:
    """Individual GEE health check endpoint."""
    import os
    from pathlib import Path
    
    try:
        gee_key_path = os.environ.get("GEE_PRIVATE_KEY_PATH")
        if not gee_key_path:
            return JSONResponse(
                content={
                    "status": "degraded",
                    "message": "GEE_PRIVATE_KEY_PATH not configured"
                },
                status_code=200
            )
        
        key_exists = Path(gee_key_path).exists()
        if key_exists:
            return JSONResponse(
                content={
                    "status": "healthy",
                    "message": "GEE credentials file found"
                },
                status_code=200
            )
        else:
            return JSONResponse(
                content={
                    "status": "degraded",
                    "message": f"GEE credentials file not found: {gee_key_path}"
                },
                status_code=200
            )
    except Exception as e:
        return JSONResponse(
            content={
                "status": "unhealthy",
                "message": f"Error checking GEE: {str(e)[:100]}"
            },
            status_code=503
        )
