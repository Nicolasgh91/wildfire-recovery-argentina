import time
from collections import defaultdict
from typing import Dict

from starlette.middleware.base import BaseHTTPMiddleware


request_metrics = defaultdict(lambda: {"count": 0, "errors": 0, "total_ms": 0.0})


def reset_metrics() -> None:
    request_metrics.clear()


def build_metrics_snapshot() -> Dict[str, Dict[str, float]]:
    return {
        path: {
            "count": metrics["count"],
            "avg_ms": round(metrics["total_ms"] / metrics["count"], 2)
            if metrics["count"]
            else 0.0,
            "error_rate": round(metrics["errors"] / metrics["count"], 4)
            if metrics["count"]
            else 0.0,
        }
        for path, metrics in request_metrics.items()
    }


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000

        key = f"{request.method} {request.url.path}"
        metrics = request_metrics[key]
        metrics["count"] += 1
        metrics["total_ms"] += duration_ms
        if response.status_code >= 400:
            metrics["errors"] += 1

        return response
