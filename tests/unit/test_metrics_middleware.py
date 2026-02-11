import anyio
from starlette.requests import Request
from starlette.responses import Response

from app.core.metrics import MetricsMiddleware, request_metrics, reset_metrics


def _build_request(path: str = "/test") -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": path,
        "headers": [],
        "query_string": b"",
        "scheme": "http",
        "server": ("testserver", 80),
        "client": ("testclient", 1234),
    }
    return Request(scope)


def test_metrics_middleware_counts_and_errors():
    reset_metrics()
    middleware = MetricsMiddleware(lambda scope, receive, send: None)

    async def ok_call_next(_):
        return Response("ok", status_code=200)

    async def err_call_next(_):
        return Response("err", status_code=500)

    anyio.run(middleware.dispatch, _build_request(), ok_call_next)
    anyio.run(middleware.dispatch, _build_request(), err_call_next)

    metrics = request_metrics["GET /test"]
    assert metrics["count"] == 2
    assert metrics["errors"] == 1
    assert metrics["total_ms"] > 0
