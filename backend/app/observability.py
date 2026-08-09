from __future__ import annotations

import time
from collections.abc import Callable

from fastapi import APIRouter, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

REQUESTS = Counter("tar_http_requests_total", "HTTP requests", ["method", "path", "status"])
LATENCY = Histogram("tar_http_request_duration_seconds", "HTTP request latency", ["method", "path"])
INFLIGHT = Gauge("tar_http_requests_inflight", "In-flight HTTP requests")

router = APIRouter(tags=["operations"])


def _route_label(request: Request) -> str:
    route = request.scope.get("route")
    return getattr(route, "path", request.url.path)


async def metrics_middleware(request: Request, call_next: Callable):
    started = time.perf_counter()
    INFLIGHT.inc()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        return response
    finally:
        path = _route_label(request)
        elapsed = time.perf_counter() - started
        REQUESTS.labels(request.method, path, str(status)).inc()
        LATENCY.labels(request.method, path).observe(elapsed)
        INFLIGHT.dec()


@router.get("/metrics", include_in_schema=False)
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
