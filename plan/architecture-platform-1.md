---
goal: Plataforma Marketplace Salões - Implementação Arquitetural e Funcional Fases 1-6
version: 1.0
date_created: 2025-10-14
last_updated: 2025-10-14
owner: Plataforma / Engenharia
status: 'Planned'
tags: [architecture, feature, backend, fastapi, postgres, scheduling, payments]
---

# Introduction

![Status: Planned](https://img.shields.io/badge/status-Planned-blue)

Plano de implementação determinístico para construir a plataforma marketplace de salões conforme PRD (`prd.md`) e 50 user stories (issues GH-001..GH-050). Abrange fundações arquiteturais, módulos funcionais, integrações terceiras, observabilidade, segurança e conformidade (LGPD). Estruturado em fases incrementais (1..6) alinhadas à matriz de roadmap existente, com tarefas atômicas, rastreáveis e validadas por critérios objetivos.

## 1. Requirements & Constraints

- **REQ-001**: Suportar cadastro/login seguro (GH-001..GH-003, GH-026, GH-041).
- **REQ-002**: Gerenciar entidades (salão, unidade, profissional, serviços) (GH-004..GH-006, GH-047).
- **REQ-003**: Motor de agenda: disponibilidade, busca de slots, reserva, status (GH-007..GH-009, GH-036..GH-037, GH-043..GH-044, GH-049, GH-050).
- **REQ-004**: Políticas de cancelamento e no-show (GH-010, GH-011, GH-032, GH-038).
- **REQ-005**: Pagamentos Pix, cartão, reembolso, logs, comissões, descontos (GH-014, GH-015, GH-021, GH-033, GH-039, GH-048).
- **REQ-006**: Notificações lembrete e fila de espera (GH-016, GH-030).
- **REQ-007**: Avaliações, moderação, filtros e busca por avaliação (GH-017, GH-018, GH-034, GH-035).
- **REQ-008**: Fidelidade e resgate (GH-022, GH-023, GH-048).
- **REQ-009**: Relatórios e métricas (GH-019, GH-020, GH-031, GH-040).
- **REQ-010**: Observabilidade e auditoria (GH-024, GH-025, GH-045).
- **REQ-011**: LGPD: anonimização e exportação (GH-027, GH-046).
- **REQ-012**: Pesquisa por localização (GH-042) & filtros combinados (GH-035).
- **PER-001**: P95 API < 800ms para endpoints críticos de busca/slots.
- **PER-002**: Throughput inicial alvo: 50 reservas/dia (dimensionar para >10x sem refator).
- **SEC-001**: JWT com refresh tokens rotacionáveis; revogação (list/deny ou key rotation) (GH-041).
- **SEC-002**: Rate limiting login (GH-026) e proteção brute-force.
- **SEC-003**: Controle de acesso baseado em papéis (Admin, Recepção, Profissional, Cliente, Franquia) (GH-024).
- **SEC-004**: Segregar segredos via variáveis de ambiente (.env + vault futuro).
- **COM-001**: Conformidade LGPD (pseudonimização, direito ao esquecimento, exportação).
- **CON-001**: Stack base: FastAPI + PostgreSQL 15 + Redis (cache/filas) + Celery/Worker.
- **CON-002**: Infra inicial containerizada (Docker) pronta para escalonamento horizontal.
- **CON-003**: Integrar no mínimo um gateway pagamento (Stripe / Pagar.me) com abstração extensível.
- **CON-004**: Zero downtime migrations (Alembic + estratégia online).
- **GUD-001**: Domain-driven package layout para clareza (core domains isolados).
- **GUD-002**: Test-first em camadas críticas (agenda, pagamentos, políticas) com cobertura >80% domínio.
- **PAT-001**: Pattern Service Layer + Repository por agregado.
- **PAT-002**: Outbox + worker para eventos externos (pagamentos, notificações) evitando inconsistências.
- **PAT-003**: Idempotency keys para criação de reservas e webhooks.
- **PAT-004**: Policy Objects para cancelamento/no-show.
- **PAT-005**: Strategy pattern para cálculo de comissão e aplicação de descontos.
- **OBS-001**: Logging estruturado (JSON) + tracing (OpenTelemetry) + métricas Prometheus.

## 2. Implementation Steps

### Convenções Gerais

Formato de caminho: `backend/<contexto>/...`. Todos endpoints em `backend/app/api/v1`. Modelos persistidos em `backend/app/db/models`. Repositórios em `backend/app/db/repositories`. Serviços de domínio em `backend/app/domain/<bounded_context>/services`. Testes espelham árvore `tests/`.

### Implementation Phase 0 (Fundações & Infra)

- GOAL-000: Provisionar estrutura base, qualidade, migrações, segurança mínima.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-0001 | Criar estrutura diretórios backend (api, domain, db, core, workers) | | |
| TASK-0002 | Inicializar FastAPI app (`backend/app/main.py`) com healthcheck `/health` | | |
| TASK-0003 | Config .env e loader seguro (`backend/app/core/config.py`) | | |
| TASK-0004 | Config Alembic migrations (`alembic.ini`, `backend/app/db/migrations/`) | | |
| TASK-0005 | Definir models base (`BaseModel`, `TimestampMixin`) em `backend/app/db/models/base.py` | | |
| TASK-0006 | Adicionar pre-commit hooks (ruff/black/mypy) | | |
| TASK-0007 | Config Dockerfile multi-stage + docker-compose redis/postgres | | |
| TASK-0008 | Implementar logger estruturado (`backend/app/core/logging.py`) JSON | | |
| TASK-0009 | Implementar middleware tracing OpenTelemetry (`backend/app/core/tracing.py`) | | |
| TASK-0010 | Config rate limiter (slowapi/redis) base para login | | |
| TASK-0011 | Pipeline CI básico (lint, test, build) (GitHub Actions) | | |
| TASK-0012 | Especificar modelos iniciais de usuário/roles (auth) | | |
| TASK-0013 | Testes iniciais smoke (`tests/e2e/test_health.py`) | | |

### Implementation Phase 1 (Fundamentos Funcionais)

- GOAL-001: Autenticação, entidades, agenda básica (stories Fase 1).

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-0100 | Model `User` + roles enum (`backend/app/db/models/user.py`) | | |
| TASK-0101 | Auth JWT endpoints login/refresh/register (`backend/app/api/v1/routes/auth.py`) | | |
| TASK-0102 | Password hashing Argon2 + política senha | | |
| TASK-0103 | E-mail verificação stub (event outbox) | | |
| TASK-0104 | Models `Salon`, `Unit`, `Professional`, `Service` | | |
| TASK-0105 | CRUD serviços com versionamento leve (soft update) | | |
| TASK-0106 | Disponibilidade profissional schema (`AvailabilitySlot`) | | |
| TASK-0107 | Serviço cálculo de slots (`domain/scheduling/services/slot_service.py`) | | |
| TASK-0108 | Endpoint buscar slots (GH-008) | | |
| TASK-0109 | Endpoint criar reserva simples (GH-009) | | |
| TASK-0110 | Repositórios SQLAlchemy para entidades núcleo | | |
| TASK-0111 | Testes unidade scheduling (slot merging, gaps) | | |
| TASK-0112 | Testes integração reservas básicas | | |
| TASK-0113 | RBAC decorator / dependency FastAPI (`core/security/rbac.py`) | | |
| TASK-0114 | Documentação OpenAPI tags iniciais | | |

### Implementation Phase 2 (Pagamentos & Notificações)

- GOAL-002: Integração gateway pagamento e lembretes.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-0200 | Abstração PaymentProvider interface | | |
| TASK-0201 | Implement Stripe Provider (ou PagarMe) (`payments/providers/stripe.py`) | | |
| TASK-0202 | Model `Payment`, estados & migração | | |
| TASK-0203 | Endpoint iniciar pagamento Pix/cartão | | |
| TASK-0204 | Webhook pagamento idempotente (store events) | | |
| TASK-0205 | Serviço reconciliar status pagamento | | |
| TASK-0206 | Model `Refund` + endpoint reembolso | | |
| TASK-0207 | Logs pagamento consulta filtrável | | |
| TASK-0208 | Fila Celery para envio lembretes (`workers/notifications.py`) | | |
| TASK-0209 | Template mensagem lembrete + fallback e-mail | | |
| TASK-0210 | Testes integração pagamentos mocks | | |
| TASK-0211 | Testes idempotência webhooks | | |
| TASK-0212 | Métricas de sucesso/falha pagamentos Prometheus | | |

### Implementation Phase 3 (Políticas, Relatórios Iniciais)

- GOAL-003: Políticas cancelamento, no-show, relatórios base.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-0300 | Policy objects cancelamento tiers | | |
| TASK-0301 | Aplicar taxa cancelamento em reserva | | |
| TASK-0302 | No-show workflow + job marcar (GH-011) | | |
| TASK-0303 | Model `AuditEvent` + logger auditoria | | |
| TASK-0304 | Materialized view ocupação (`mv_occupancy`) | | |
| TASK-0305 | Endpoint relatórios operacionais (GH-019) | | |
| TASK-0306 | Endpoint relatórios plataforma (GH-020) | | |
| TASK-0307 | Endpoint ajustar status reserva (GH-043) | | |
| TASK-0308 | Histórico reservas cliente (GH-044) | | |
| TASK-0309 | Bloqueio no-show threshold (GH-032) | | |
| TASK-0310 | Testes políticas & edge cases datas | | |
| TASK-0311 | Testes agregações relatórios | | |

### Implementation Phase 4 (Agenda Avançada, Avaliações, Fidelidade)

- GOAL-004: Fila espera, overbooking controlado, avaliações, fidelidade.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-0400 | Model `WaitlistEntry` + endpoint criar/listar | | |
| TASK-0401 | Overbooking policy + flag unidade | | |
| TASK-0402 | Pacote multi-serviço reserva transacional | | |
| TASK-0403 | Reagendar reserva política valida (base) | | |
| TASK-0404 | Notificação liberação fila (GH-030) | | |
| TASK-0405 | Model `Review` + endpoint avaliar (GH-017) | | |
| TASK-0406 | Moderação avaliações (GH-018) | | |
| TASK-0407 | Model `LoyaltyLedger` + acúmulo pontos (GH-022) | | |
| TASK-0408 | Resgate pontos e impacto pagamento (GH-023) | | |
| TASK-0409 | Testes transação pacotes rollback | | |
| TASK-0410 | Testes ranking e média avaliações | | |
| TASK-0411 | Testes contabilidade pontos | | |

### Implementation Phase 5 (Segurança Avançada, Auditoria, Performance)

- GOAL-005: Endurecer segurança, comissões, painéis, exportações.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-0500 | RBAC refinado / escopos (GH-024) | | |
| TASK-0501 | Auditoria eventos (persist + consulta) | | |
| TASK-0502 | Rate limiting login final (produção) | | |
| TASK-0503 | Anonimização PII (GH-027) | | |
| TASK-0504 | Exportar dados pessoais (GH-046) | | |
| TASK-0505 | Cálculo comissão profissional (GH-021) | | |
| TASK-0506 | Painel desempenho profissional (GH-040) | | |
| TASK-0507 | Exportação relatórios CSV (GH-031) | | |
| TASK-0508 | Pesquisa por localização (GH-042) | | |
| TASK-0509 | Monitoramento erros Sentry (GH-045) | | |
| TASK-0510 | Otimizações índices performance críticos | | |
| TASK-0511 | Testes performance carga (locust/k6) | | |

### Implementation Phase 6 (Expansões & Otimizações Finais)

- GOAL-006: Ajustes avançados e promoções.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-0600 | Reagendamento avançado (GH-028) | | |
| TASK-0601 | Filtro preço+avaliação composto (GH-035) | | |
| TASK-0602 | Busca avaliações paginada (GH-034) | | |
| TASK-0603 | Atualizar dados salão (GH-047) | | |
| TASK-0604 | Desconto promocional (GH-048) | | |
| TASK-0605 | Cancelamento pela recepção (GH-049) | | |
| TASK-0606 | Visualizar fila espera recepção (GH-050) | | |
| TASK-0607 | Refino caching (Redis) slots e catálogos | | |
| TASK-0608 | Hardening segurança final (headers CSP) | | |
| TASK-0609 | Revisão dívida técnica consolidada | | |

## 3. Alternatives

- **ALT-001**: Usar monólito Django em vez de FastAPI + libs — descartado para manter performance e granularidade de componentes assíncronos.
- **ALT-002**: Usar microservices antecipados — descartado (overhead infra e complexidade) antes de validar domínio consolidado.
- **ALT-003**: Usar cron para notificações em vez de fila — descartado por necessidade de escalabilidade e idempotência robusta.
- **ALT-004**: Tratar pagamentos síncronos direto no request — descartado para evitar timeouts e permitir retries outbox.

## 4. Dependencies

- **DEP-001**: FastAPI, Uvicorn, SQLAlchemy 2.x, Alembic.
- **DEP-002**: PostgreSQL 15 com extensões (btree_gist, pg_trgm para busca parcial se necessário).
- **DEP-003**: Redis (cache, rate limit, filas celery ou RQ).
- **DEP-004**: Payment Gateway (Stripe ou Pagar.me) SDK.
- **DEP-005**: Email provider (SendGrid / SES) abstração futura.
- **DEP-006**: WhatsApp Business API / Twilio (notificações fallback).
- **DEP-007**: Sentry (monitoramento de erros).
- **DEP-008**: OpenTelemetry SDK + Prometheus exporter.
- **DEP-009**: Geocoding API (opcional Fase 5) - ex: Nominatim/Google.

## 5. Files

- **FILE-001**: `backend/app/main.py` - App FastAPI + routers.
- **FILE-002**: `backend/app/core/config.py` - Config centralizada.
- **FILE-003**: `backend/app/core/security/jwt.py` - Geração/validação tokens.
- **FILE-004**: `backend/app/domain/scheduling/services/slot_service.py` - Lógica de slots.
- **FILE-005**: `backend/app/db/models/*.py` - Modelos ORM.
- **FILE-006**: `backend/app/db/repositories/*.py` - Repositórios.
- **FILE-007**: `backend/app/api/v1/routes/*.py` - Endpoints REST.
- **FILE-008**: `backend/app/domain/payments/providers/*.py` - Providers pagamento.
- **FILE-009**: `backend/app/workers/*.py` - Workers Celery.
- **FILE-010**: `tests/unit/...` - Testes unidade domínio.
- **FILE-011**: `tests/integration/...` - Testes integração API/DB.
- **FILE-012**: `docker/Dockerfile` - Build multi-stage.
- **FILE-013**: `alembic/versions/*.py` - Migrações.
- **FILE-014**: `backend/app/domain/policies/*.py` - Policy objects.
- **FILE-015**: `backend/app/domain/loyalty/services/loyalty_service.py` - Pontos/resgates.

## 6. Testing

- **TEST-001**: Testes unidade scheduling (merge/corte slots).
- **TEST-002**: Testes API reserva feliz e conflitos.
- **TEST-003**: Testes idempotência criação reserva (mesma idempotency-key).
- **TEST-004**: Testes webhooks pagamento (assinatura e repetição).
- **TEST-005**: Testes políticas cancelamento multi-tier (limites fronteira tempo).
- **TEST-006**: Testes no-show bloqueio e desbloqueio após período.
- **TEST-007**: Testes avaliações média e distribuição.
- **TEST-008**: Testes pontos acúmulo/resgate e saldo consistente.
- **TEST-009**: Testes anonimização (PII removida, agregados preservados).
- **TEST-010**: Testes exportação dados pessoais (formato, autorização).
- **TEST-011**: Testes performance (k6) endpoints slots e busca (latência P95).
- **TEST-012**: Testes RBAC endpoints restritos (tentativas sem permissão).
- **TEST-013**: Testes rate limiting login (excedente bloqueia).
- **TEST-014**: Testes busca/filtragem avaliações e ordenação.

## 7. Risks & Assumptions

- **RISK-001**: Complexidade esquemas disponibilidade → Mitigar com testes robustos e design incremental.
- **RISK-002**: Latência gateway pagamento externa → Timeout configurável + retries exponenciais.
- **RISK-003**: Crescimento rápido demanda > arquitetura monolítica → Modularização pronta para extração futura.
- **RISK-004**: Inconsistência eventos (webhook vs DB) → Outbox + idempotência.
- **RISK-005**: LGPD mudanças regulatórias → Config flag data retention central.
- **RISK-006**: Custos Redis/Sentry em escala → Monitorar métricas uso, tuning TTL cache.
- **ASSUMPTION-001**: Volume inicial moderado permite single DB primário.
- **ASSUMPTION-002**: Gateways pagamento suportam webhooks confiáveis.
- **ASSUMPTION-003**: Time dispõe de conhecimento Python/FastAPI.

## 8. Related Specifications / Further Reading

- `prd.md` (Requisitos detalhados & user stories)  
- `issues/README.md` (Índice de issues, épicos e fases)  
- OWASP Top 10 (segurança)  
- PCI-DSS guidelines (pagamentos - referência futura)  
- OpenTelemetry Spec (observabilidade)  
