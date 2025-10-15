"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from backend.app.core.config import settings
from backend.app.core.logging import setup_logging
from backend.app.core.metrics import (
    PrometheusMiddleware,
    metrics_endpoint,
)
from backend.app.core.rate_limit import limiter
from backend.app.core.tracing import setup_tracing


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    setup_logging()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Beauty Salon Marketplace Platform",
    lifespan=lifespan,
)

# Add middlewares
app.add_middleware(PrometheusMiddleware)

# Setup tracing
setup_tracing(app)

# Add rate limiter
app.state.limiter = limiter


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint for monitoring and load balancers."""
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "service": settings.PROJECT_NAME,
            "version": settings.VERSION,
        },
    )


@app.get("/metrics", tags=["Monitoring"])
async def metrics():
    """Prometheus metrics endpoint."""
    return await metrics_endpoint()
