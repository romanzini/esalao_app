"""Prometheus metrics middleware and endpoints."""

from prometheus_client import Counter, Histogram, generate_latest
from prometheus_client.core import CollectorRegistry
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Create registry
registry = CollectorRegistry()

# Metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code'],
    registry=registry
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint'],
    registry=registry
)


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Middleware to collect HTTP metrics."""

    async def dispatch(self, request: Request, call_next):
        """Process request and collect metrics."""
        # Skip metrics endpoint itself
        if request.url.path == "/metrics":
            return await call_next(request)

        method = request.method
        path = request.url.path

        # Start timer
        with http_request_duration_seconds.labels(
            method=method,
            endpoint=path
        ).time():
            response = await call_next(request)

        # Record metrics
        http_requests_total.labels(
            method=method,
            endpoint=path,
            status_code=response.status_code
        ).inc()

        return response


async def metrics_endpoint():
    """Expose Prometheus metrics."""
    return Response(
        generate_latest(registry),
        media_type="text/plain"
    )
