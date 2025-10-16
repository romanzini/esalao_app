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
from backend.app.api.v1 import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    setup_logging()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="""
# Beauty Salon Marketplace Platform API

API completa para marketplace de agendamento de serviços de beleza.

## Funcionalidades Principais

- **Autenticação**: Sistema completo de registro, login e refresh de tokens JWT
- **Agendamento**: Busca de slots disponíveis e criação de reservas
- **Gestão de Reservas**: CRUD completo com controle de status e cancelamento
- **Profissionais**: Gerenciamento de perfis de profissionais
- **Serviços**: Catálogo de serviços com preços e durações
- **RBAC**: Controle de acesso baseado em papéis (Admin, Client, Professional, Receptionist)

## Autenticação

A API utiliza **JWT Bearer Tokens** para autenticação.

1. Registre-se via `POST /api/v1/auth/register` ou faça login via `POST /api/v1/auth/login`
2. Utilize o `access_token` retornado no header `Authorization: Bearer {token}`
3. Quando o token expirar, use `POST /api/v1/auth/refresh` com o `refresh_token`

## Rate Limiting

- **Login**: Máximo de 5 tentativas por minuto por IP
- **Outros endpoints**: 100 requisições por minuto por IP
    """,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    swagger_ui_parameters={
        "docExpansion": "none",
        "filter": True,
        "tryItOutEnabled": True,
        "persistAuthorization": True,
    },
)

# Add middlewares
app.add_middleware(PrometheusMiddleware)

# Setup tracing
setup_tracing(app)

# Add rate limiter
app.state.limiter = limiter

# Include API routers
app.include_router(api_router)


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
