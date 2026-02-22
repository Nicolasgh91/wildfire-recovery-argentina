import logging
import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("forestguard.latency")

# Service Level Objectives (SLOs) - Max latency definitions
# Can be moved to config or DB in future
SLO_THRESHOLDS = {
    "/api/v1/fires/": 0.400,  # 400ms for listing fires (UC-13)
    "/api/v1/audit/land-use": 1.500,  # 1.5s for complex geospatial audit
    "/api/v1/health": 0.200,  # 200ms for health check
}


class DeprecationMiddleware(BaseHTTPMiddleware):
    """
    Adds deprecation headers to responses as per RFC 8594.
    """

    def __init__(
        self,
        app,
        date: str = "2026-04-30",
        link: str = "https://docs.forestguard.ar/migration-guide",
    ):
        super().__init__(app)
        self.deprecation_date = date
        self.migration_link = link

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        # RFC 8594 Headers
        response.headers[
            "Deprecation"
        ] = f'date="{self.deprecation_date}"'  # Or version
        response.headers["Link"] = f'<{self.migration_link}>; rel="deprecation"'
        return response


class LatencyMonitorMiddleware(BaseHTTPMiddleware):
    """
    Middleware to monitor request latency and check against defined SLOs.
    Logs warnings if SLO is breached.
    """

    async def dispatch(self, request: Request, call_next):
        start_time = time.perf_counter()

        response = await call_next(request)

        process_time = time.perf_counter() - start_time

        # Add processing time to headers for transparency
        response.headers["X-Process-Time"] = str(process_time)

        self._check_slo(request.url.path, process_time)

        return response

    def _check_slo(self, path: str, duration: float):
        # Match path against configured SLOs
        # Sort by length desc to match most specific path first?
        # For simplicity, exact match or simple prefix

        budget = None
        matched_path = None

        # Try finding a budget
        # We start looking for exact matches (ignoring trailing slash issues if needed)
        # Note: request.url.path usually includes leading slash

        for slo_path, limit in SLO_THRESHOLDS.items():
            # Check for exact match or directory match
            if path == slo_path or (
                slo_path.endswith("/") and path.startswith(slo_path)
            ):
                # If we have multiple matches (rare for this simple dict), take the first one or logic needs improvement
                budget = limit
                matched_path = slo_path
                break

        if budget and duration > budget:
            logger.warning(
                f"SLO_BREACH | Endpoint: {path} | Duration: {duration:.4f}s | Budget: {budget:.3f}s"
            )
            # In a real system, increment a Prometheus counter here:
            # slo_breach_total.labels(endpoint=path).inc()


class RequestIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add X-Request-ID header for distributed tracing.

    If the client sends X-Request-ID, it is preserved.
    Otherwise, a new UUID is generated.

    The request ID is:
    - Available in request.state.request_id for logging
    - Returned in response headers for client correlation
    """

    async def dispatch(self, request: Request, call_next):
        import uuid

        # Use client-provided ID or generate new one
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            request_id = str(uuid.uuid4())

        # Store in request state for access in endpoint handlers
        request.state.request_id = request_id

        # Log the request with ID for tracing
        logger.info(
            f"REQUEST | id={request_id} | method={request.method} | path={request.url.path}"
        )

        response = await call_next(request)

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id

        return response
