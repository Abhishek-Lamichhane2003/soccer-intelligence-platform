from __future__ import annotations

import time
from fastapi import Request
from prometheus_client import Counter, Histogram
from starlette.middleware.base import BaseHTTPMiddleware

REQUESTS = Counter(
    'soccer_http_requests_total',
    'Total HTTP requests processed by the API',
    ['method', 'path', 'status'],
)
LATENCY = Histogram(
    'soccer_http_request_duration_seconds',
    'HTTP request latency in seconds',
    ['method', 'path'],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2, 5),
)


class RequestMetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        elapsed = time.perf_counter() - start
        route = request.scope.get('route')
        path = getattr(route, 'path', request.url.path)
        REQUESTS.labels(request.method, path, str(response.status_code)).inc()
        LATENCY.labels(request.method, path).observe(elapsed)
        return response
