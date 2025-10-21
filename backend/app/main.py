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
from backend.app.middleware.audit import AuditMiddleware
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

API completa para marketplace de agendamento de serviços de beleza com sistema avançado de políticas, auditoria e relatórios.

## Funcionalidades Principais

### Core Features
- **Autenticação**: Sistema completo de registro, login e refresh de tokens JWT
- **Agendamento**: Busca de slots disponíveis e criação de reservas
- **Gestão de Reservas**: CRUD completo com controle de status e cancelamento
- **Profissionais**: Gerenciamento de perfis de profissionais
- **Serviços**: Catálogo de serviços com preços e durações
- **RBAC**: Controle de acesso baseado em papéis (Admin, Client, Professional, Receptionist)

### Phase 3: Policies & Reporting (NEW)
- **Políticas de Cancelamento**: Sistema hierárquico de taxas por tempo de antecedência
- **Detecção de No-Show**: Sistema automatizado de identificação e marcação
- **Auditoria**: Rastreamento completo de eventos do sistema
- **Relatórios Operacionais**: Dashboard e métricas para salões
- **Relatórios de Plataforma**: Analytics administrativos cross-salon
- **Otimização de Performance**: Cache Redis e queries otimizadas

## Autenticação

A API utiliza **JWT Bearer Tokens** para autenticação.

1. Registre-se via `POST /api/v1/auth/register` ou faça login via `POST /api/v1/auth/login`
2. Utilize o `access_token` retornado no header `Authorization: Bearer {token}`
3. Quando o token expirar, use `POST /api/v1/auth/refresh` com o `refresh_token`

## Estrutura de Endpoints

### 🔐 Autenticação (`/auth`)
- Registro e login de usuários
- Refresh de tokens JWT
- Controle de sessões

### 📅 Agendamento (`/bookings`, `/scheduling`)
- Busca de slots disponíveis
- Criação e gestão de reservas
- Cancelamento com políticas

### 👥 Gestão (`/professionals`, `/services`)
- Cadastro de profissionais
- Catálogo de serviços
- Configuração de disponibilidades

### 💰 Pagamentos (`/payments`, `/refunds`)
- Processamento de pagamentos
- Sistema de reembolsos
- Métricas financeiras

### 🎯 Políticas e Auditoria (`/cancellation-policies`, `/audit`)
- Políticas tiered de cancelamento
- Sistema de auditoria completo
- Rastreamento de eventos

### 📊 Relatórios (`/reports`, `/platform-reports`, `/optimized-reports`)
- Dashboard operacional
- Analytics de plataforma
- Relatórios otimizados com cache

### 🚫 No-Show (`/no-show-jobs`)
- Detecção automatizada
- Jobs de processamento
- Configuração de regras

### 🔔 Notificações (`/notifications`)
- Sistema de notificações
- Templates customizáveis
- Integração com webhooks

### 🎁 Fidelidade (`/loyalty`, `/waitlist`)
- Programa de pontos
- Lista de espera
- Recompensas

## Níveis de Acesso

### 👤 Client
- Visualizar serviços e profissionais
- Criar e gerenciar suas próprias reservas
- Acessar histórico pessoal

### 💼 Professional
- Gerenciar própria agenda
- Configurar disponibilidades
- Acessar relatórios de performance

### 🏢 Salon Owner
- Gestão completa do salão
- Relatórios operacionais
- Configuração de políticas

### ⚡ Admin
- Acesso completo ao sistema
- Relatórios de plataforma
- Gestão de usuários e políticas globais

## Rate Limiting

A API implementa rate limiting para proteger contra abuso:
- **Login**: 5 tentativas por minuto
- **Geral**: 100 requests por minuto por IP
- **Reports**: 20 requests por minuto (cache-aware)

## Performance e Cache

O sistema utiliza **Redis** para otimização:
- Cache de relatórios (TTL configurável)
- Sessions e rate limiting
- Query optimization automática

## Monitoring e Auditoria

- **Prometheus Metrics**: Métricas detalhadas de performance
- **Audit Events**: Log completo de ações críticas
- **Distributed Tracing**: Rastreamento de requests
- **Health Checks**: Monitoramento de saúde da API

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
app.add_middleware(AuditMiddleware)

# Setup tracing
setup_tracing(app)

# Add rate limiter
app.state.limiter = limiter

# Include API routers
app.include_router(api_router, prefix="/api")


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
