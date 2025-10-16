---
goal: Plataforma Marketplace de Salões - Plano de Implementação End-to-End
version: 1.0
date_created: 2025-10-15
last_updated: 2025-10-15
owner: Engenharia Plataforma
status: 'Planned'
tags: [feature, architecture, backend, fastapi, postgres, scheduling, payments, security, observability]
---

# Introduction

![Status: Planned](https://img.shields.io/badge/status-Planned-blue)

Plano determinístico e executável para implementar a plataforma (backend monolito modular FastAPI + PostgreSQL + Redis + Celery) cobrindo todas as 50 user stories (GH-001..GH-050) em fases incrementais. Cada tarefa define artefatos, critérios de conclusão e dependências explícitas para permitir execução paralela controlada por qualquer agente humano ou automatizado.

## 1. Requirements & Constraints

- **REQ-001**: Autenticação segura (GH-001..GH-003, GH-026, GH-041).
- **REQ-002**: Gestão de entidades (salão, unidade, profissional, serviços) (GH-004..GH-006, GH-047).
- **REQ-003**: Agenda e reservas (slots, criação, status, histórico) (GH-007..GH-009, GH-036..GH-037, GH-043..GH-044, GH-049, GH-050).
- **REQ-004**: Políticas cancelamento / no-show (GH-010, GH-011, GH-032, GH-038).
- **REQ-005**: Pagamentos & reembolsos (GH-014, GH-015, GH-021, GH-033, GH-039, GH-048).
- **REQ-006**: Notificações lembrete & fila espera (GH-016, GH-030).
- **REQ-007**: Avaliações & moderação (GH-017, GH-018, GH-034, GH-035).
- **REQ-008**: Fidelidade & pontos (GH-022, GH-023, GH-048).
- **REQ-009**: Relatórios & exportações (GH-019, GH-020, GH-031, GH-040).
- **REQ-010**: Observabilidade & auditoria (GH-024, GH-025, GH-045).
- **REQ-011**: LGPD (anonimização & exportação) (GH-027, GH-046).
- **REQ-012**: Busca & filtros (localização, preço+avaliação) (GH-042, GH-035).
- **PER-001**: P95 < 800ms em endpoints críticos (slots, busca, reserva criação).
- **PER-002**: Escalabilidade para 500 reservas/dia sem refator estrutural (dimensionamento inicial + headroom 10x).
- **SEC-001**: JWT com refresh rotativo e revogação.
- **SEC-002**: Rate limiting login e endpoints sensíveis.
- **SEC-003**: RBAC multi-papéis (Admin, Recepção, Profissional, Cliente, Franquia).
- **SEC-004**: Proteção idempotência em reservas e webhooks.
- **COM-001**: Conformidade LGPD (direito de exclusão e portabilidade).
- **CON-001**: Stack fixa: FastAPI, SQLAlchemy 2, PostgreSQL 15, Redis, Celery, Alembic.
- **CON-002**: Deployment containerizado (Docker multi-stage) + docker-compose dev.
- **GUD-001**: Test coverage domínio crítico ≥ 80% (agenda, pagamentos, políticas).
- **GUD-002**: Logging estruturado JSON + tracing OpenTelemetry.
- **PAT-001**: Service Layer + Repository por agregado.
- **PAT-002**: Outbox para eventos assíncronos (pagamentos/notifications).
- **PAT-003**: Policy Objects (cancelamento/no-show).
- **PAT-004**: Strategy (cálculo comissões / descontos / fidelidade).
- **PAT-005**: Idempotency Keys (reservas, webhooks pagamentos).

## 2. Implementation Steps

### Implementation Phase 0 (Fundações / Infra)

- GOAL-000: Estruturar base técnica, observabilidade mínima, segurança inicial e pipeline.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-0001 | Criar diretórios `backend/app/{api,core,db,domain,workers}` e `tests/` | ✅ | 2025-10-15 |
| TASK-0002 | Implementar `backend/app/main.py` com FastAPI, `/health` GET 200 | ✅ | 2025-10-15 |
| TASK-0003 | Criar `backend/app/core/config.py` com pydantic settings e load `.env` | ✅ | 2025-10-15 |
| TASK-0004 | Config Alembic (`alembic.ini`, pasta `alembic/versions`) + script upgrade | ✅ | 2025-10-15 |
| TASK-0005 | Base ORM: `backend/app/db/models/base.py` com `Base`, mixins id/ts | ✅ | 2025-10-15 |
| TASK-0006 | Dockerfile multi-stage + `docker-compose.yml` (api, db, redis, worker) | ✅ | 2025-10-15 |
| TASK-0007 | Pre-commit (ruff, black, mypy) + `pyproject.toml` | ✅ | 2025-10-15 |
| TASK-0008 | Logging JSON (`backend/app/core/logging.py`) + intercept std logging | ✅ | 2025-10-15 |
| TASK-0009 | OpenTelemetry tracing (`backend/app/core/tracing.py`) + exporter console | ✅ | 2025-10-15 |
| TASK-0010 | Métricas Prometheus (`/metrics`) via middleware | ✅ | 2025-10-15 |
| TASK-0011 | Rate limit infra base (slowapi + redis) configurada | ✅ | 2025-10-15 |
| TASK-0012 | Pipeline CI GitHub Actions (lint + test + build docker) | ✅ | 2025-10-15 |
| TASK-0013 | Teste inicial `tests/e2e/test_health.py` green | ✅ | 2025-10-15 |

### Implementation Phase 1 (Auth, Entidades, Agenda Básica)

- GOAL-001: Funcionalidades essenciais de cadastro/login e slot básico de reserva.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-0100 | Model `User` + hashing Argon2 (`backend/app/db/models/user.py`) | ✅ | 2025-10-15 |
| TASK-0101 | JWT utils (`backend/app/core/security/jwt.py`) + refresh rotation | ✅ | 2025-10-15 |
| TASK-0102 | Endpoints auth (`backend/app/api/v1/routes/auth.py`) login/register/refresh | ✅ | 2025-10-15 |
| TASK-0103 | Models `Salon`, `Professional`, `Service`, `Availability`, `Booking` (`db/models/`) | ✅ | 2025-10-15 |
| TASK-0104 | Repositórios entidades (`db/repositories/user.py`) CRUD básico | ✅ | 2025-10-16 |
| TASK-0105 | Migração Alembic tabelas core (`alembic/versions/891c705f503c`) | ✅ | 2025-10-16 |
| TASK-0106 | Serviço slot merge `domain/scheduling/services/slot_service.py` | ⏳ | |
| TASK-0107 | Endpoint buscar slots (`routes/scheduling.py`) | ⏳ | |
| TASK-0108 | Endpoint criar reserva básica (`routes/bookings.py`) | ⏳ | |
| TASK-0109 | RBAC decorator `core/security/rbac.py` + endpoint /me | ✅ | 2025-10-16 |
| TASK-0110 | Documentação OpenAPI inicial (tags Auth, Scheduling) | 🔄 | Auth OK |
| TASK-0111 | Testes unidade slots (gaps, overlaps) | ⏳ | |
| TASK-0112 | Testes integração auth + reserva happy path | ⏳ | |

### Implementation Phase 2 (Pagamentos & Notificações)

- GOAL-002: Integração gateway, fluxo pagamento e lembretes reserva.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-0200 | Interface `PaymentProvider` (`domain/payments/provider.py`) | | |
| TASK-0201 | Implement provider Stripe/PagarMe (`providers/stripe.py`) | | |
| TASK-0202 | Models `Payment`, `Refund` + enums status | | |
| TASK-0203 | Endpoint iniciar pagamento (`routes/payments.py`) | | |
| TASK-0204 | Webhook pagamento idempotente + tabela outbox | | |
| TASK-0205 | Serviço reconciliação estado (`payments/services/reconcile.py`) | | |
| TASK-0206 | Endpoint reembolso (parcial/integral) | | |
| TASK-0207 | Logs pagamento consulta (filtros) | | |
| TASK-0208 | Worker Celery lembretes (`workers/notifications.py`) | | |
| TASK-0209 | Template mensagem + fallback e-mail | | |
| TASK-0210 | Testes integração pagamentos (mock gateway) | | |
| TASK-0211 | Testes idempotência webhooks repetidos | | |
| TASK-0212 | Métricas pagamentos (sucesso, falha, tempo) | | |

### Implementation Phase 3 (Políticas & Relatórios Iniciais)

- GOAL-003: Cancelamento, no-show, auditoria e relatórios base.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-0300 | Policy cancelamento tiers (`domain/policies/cancellation.py`) | | |
| TASK-0301 | Aplicar taxa cancelamento no fluxo reserva | | |
| TASK-0302 | Workflow no-show + job agendado | | |
| TASK-0303 | Model + persist `AuditEvent` | | |
| TASK-0304 | Views/mv relatórios ocupação | | |
| TASK-0305 | Endpoint relatórios operacionais | | |
| TASK-0306 | Endpoint relatórios plataforma | | |
| TASK-0307 | Ajustar status reserva endpoint (GH-043) | | |
| TASK-0308 | Histórico reservas cliente endpoint | | |
| TASK-0309 | Bloqueio no-show logic + threshold | | |
| TASK-0310 | Testes políticas (fronteiras tempo) | | |
| TASK-0311 | Testes relatórios agregações | | |

### Implementation Phase 4 (Agenda Avançada, Avaliações, Fidelidade)

- GOAL-004: Recursos avançados de agenda, avaliações e pontos.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-0400 | Waitlist model/endpoint (`domain/scheduling/waitlist.py`) | | |
| TASK-0401 | Overbooking controlado flag unidade | | |
| TASK-0402 | Reserva multi-serviço transacional | | |
| TASK-0403 | Reagendar reserva (básico + conflitos) | | |
| TASK-0404 | Notificação liberação fila | | |
| TASK-0405 | Model `Review` + endpoint avaliar | | |
| TASK-0406 | Moderação avaliações (status) | | |
| TASK-0407 | Loyalty ledger + acúmulo | | |
| TASK-0408 | Resgate pontos integrando pagamento | | |
| TASK-0409 | Testes transação pacotes rollback | | |
| TASK-0410 | Testes ranking avaliações | | |
| TASK-0411 | Testes contabilidade pontos | | |

### Implementation Phase 5 (Segurança, Compliance, Performance)

- GOAL-005: Hardening segurança, exportações, comissões e painéis.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-0500 | RBAC refinado escopos avançados | | |
| TASK-0501 | Anonimização PII (GH-027) | | |
| TASK-0502 | Exportar dados pessoais (GH-046) | | |
| TASK-0503 | Comissão profissional cálculo (Strategy) | | |
| TASK-0504 | Painel desempenho profissional (GH-040) | | |
| TASK-0505 | Exportação relatórios CSV (GH-031) | | |
| TASK-0506 | Pesquisa localização (GH-042) | | |
| TASK-0507 | Monitoramento erros Sentry + dashboards | | |
| TASK-0508 | Índices performance tuning | | |
| TASK-0509 | Testes carga (k6/locust) endpoints críticos | | |
| TASK-0510 | Headers segurança (CSP, HSTS) | | |

### Implementation Phase 6 (Promoções & Otimizações Finais)

- GOAL-006: Descontos, refinamentos busca, limpeza técnica.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-0600 | Filtro composto preço+avaliação | | |
| TASK-0601 | Busca avaliações paginada | | |
| TASK-0602 | Atualizar dados salão (GH-047) | | |
| TASK-0603 | Desconto promocional (GH-048) | | |
| TASK-0604 | Cancelamento recepção (GH-049) | | |
| TASK-0605 | Visualizar fila espera recepção (GH-050) | | |
| TASK-0606 | Refino caching (slots/catalog) | | |
| TASK-0607 | Hardening final + pentest fixes | | |
| TASK-0608 | Revisão dívida técnica / backlog | | |

## 3. Alternatives

- **ALT-001**: Microservices antecipados – descartado (complexidade, overhead DevOps prematuro).
- **ALT-002**: Uso de ORM diferente (Tortoise) – descartado pela maturidade SQLAlchemy 2 + Alembic.
- **ALT-003**: Sem Outbox (chamadas diretas) – risco inconsistente em falhas; descartado.
- **ALT-004**: Webhooks síncronos no request principal – descartado por timeouts / UX.

## 4. Dependencies

- **DEP-001**: FastAPI, Uvicorn, SQLAlchemy, Alembic.
- **DEP-002**: Redis (rate limit, cache, fila Celery).
- **DEP-003**: Gateway Pagamento (Stripe/PagarMe SDK).
- **DEP-004**: Celery + Redis broker/back-end.
- **DEP-005**: OpenTelemetry SDK + Prometheus client.
- **DEP-006**: Sentry SDK.
- **DEP-007**: Biblioteca hashing Argon2.
- **DEP-008**: Geocoding API (fase posterior).

## 5. Files

- **FILE-001**: `backend/app/main.py` – bootstrap app.
- **FILE-002**: `backend/app/core/config.py` – settings central.
- **FILE-003**: `backend/app/core/security/jwt.py` – tokens.
- **FILE-004**: `backend/app/core/security/rbac.py` – RBAC decorators.
- **FILE-005**: `backend/app/db/models/*.py` – ORM models domínio.
- **FILE-006**: `backend/app/db/repositories/*.py` – CRUD isolado.
- **FILE-007**: `backend/app/domain/scheduling/services/slot_service.py` – lógica slots.
- **FILE-008**: `backend/app/domain/payments/providers/*.py` – integrações pagamento.
- **FILE-009**: `backend/app/domain/policies/*.py` – policies cancel/no-show.
- **FILE-010**: `backend/app/domain/loyalty/*.py` – fidelidade.
- **FILE-011**: `backend/app/api/v1/routes/*.py` – endpoints REST.
- **FILE-012**: `backend/app/workers/*.py` – jobs Celery.
- **FILE-013**: `tests/unit/...` – testes unidade.
- **FILE-014**: `tests/integration/...` – testes integração.
- **FILE-015**: `alembic/versions/*.py` – migrações.
- **FILE-016**: `docker/Dockerfile` – build container.
- **FILE-017**: `docker-compose.yml` – stack dev.

## 6. Testing

- **TEST-001**: Health & config smoke.
- **TEST-002**: Auth login/register + refresh rotation.
- **TEST-003**: Rate limit login excedente bloqueia.
- **TEST-004**: Slot service (overlaps, sorting, gaps) edge cases.
- **TEST-005**: Reserva idempotente repete mesma key → única linha DB.
- **TEST-006**: Webhook pagamento repetido → sem duplicar transação.
- **TEST-007**: Política cancelamento prazo limites.
- **TEST-008**: No-show bloqueio/unblock após período.
- **TEST-009**: Relatórios agregações consistentes (mock data).
- **TEST-010**: Fidelidade acúmulo/resgate saldo correto.
- **TEST-011**: Avaliações média ponderada + filtros.
- **TEST-012**: Anonimização remove PII mantendo métricas.
- **TEST-013**: Exportação dados completo + formato válido.
- **TEST-014**: Performance P95 < 800ms (k6) endpoints slots/reserva.
- **TEST-015**: RBAC nega acesso não autorizado.
- **TEST-016**: Busca localização (raio, ordenação).

## 7. Risks & Assumptions

- **RISK-001**: Complexidade agenda → Mitigar com testes abrangentes e incremental delivery.
- **RISK-002**: Falhas gateway pagamento → Retries + circuito aberto em degradação.
- **RISK-003**: Crescimento rápido → Modularização facilita extração futura de serviços.
- **RISK-004**: Custos Redis em aumento → Monitorar métricas e TTL adaptativo.
- **RISK-005**: Mudanças regulatórias LGPD → Centralizar lógica em módulo compliance.
- **RISK-006**: Gargalo relatórios pesados → Materialized views + índices.
- **ASSUMPTION-001**: Tráfego inicial moderado < 5 req/s pico.
- **ASSUMPTION-002**: Time familiar com Python async & SQLAlchemy 2.
- **ASSUMPTION-003**: Gateway pagamento oferece webhooks estáveis.

## 8. Related Specifications / Further Reading

- `plan/architecture-platform-1.md`
- `prd.md`
- `issues/README.md`
- OWASP Top 10
- OpenTelemetry Docs
- Stripe / Pagar.me API Docs

## 9. Traceability Matrix (Tasks ↔ Issues)

Tabela de rastreabilidade entre cada TASK do plano e as issues (GH-xxx). Tarefas de fundação sem ligação direta recebem marcação FOUNDATION para indicar suporte transversal.

| Task | Issues (GH-xxx) | Tipo | Notas |
|------|-----------------|------|-------|
| TASK-0001 | FOUNDATION | Infra | Estrutura diretórios base para todos domínios |
| TASK-0002 | FOUNDATION | Infra | Health endpoint suporte monitoramento inicial |
| TASK-0003 | FOUNDATION | Config | Config suporta todas features (segurança, DB) |
| TASK-0004 | FOUNDATION | DB | Migrações para todos modelos subsequentes |
| TASK-0005 | FOUNDATION | DB | Base ORM comum (timestamps / ids) |
| TASK-0006 | FOUNDATION | DevOps | Containerização geral |
| TASK-0007 | FOUNDATION | Qualidade | Padronização code style / CI |
| TASK-0008 | GH-045 | Observabilidade | Logging estruturado usado em auditoria / erros |
| TASK-0009 | GH-045 | Observabilidade | Tracing inicial (latência P95) |
| TASK-0010 | GH-045 | Observabilidade | Métricas para endpoints críticos |
| TASK-0011 | GH-026 | Segurança | Base para rate limiting login |
| TASK-0012 | FOUNDATION | DevOps | Pipeline garante qualidade contínua |
| TASK-0013 | FOUNDATION | Testes | Smoke garante base estável |
| TASK-0100 | GH-001, GH-002, GH-003, GH-026, GH-041 | Auth | Usuário + credenciais + suporte logout/rate limit |
| TASK-0101 | GH-041 | Auth | Refresh/rotacionar tokens |
| TASK-0102 | GH-001, GH-002, GH-003 | Auth | Endpoints de registro/login/recuperação |
| TASK-0103 | GH-004, GH-005, GH-006, GH-047 | Entidades | CRUD de entidades principais |
| TASK-0104 | GH-004, GH-005, GH-006 | Entidades | Repositórios persistência |
| TASK-0105 | GH-007 | Scheduling | Modelo disponibilidade |
| TASK-0106 | GH-007, GH-008 | Scheduling | Lógica cálculo slots disponíveis |
| TASK-0107 | GH-008 | Scheduling | Buscar slots endpoint |
| TASK-0108 | GH-009 | Scheduling | Criar reserva simples |
| TASK-0109 | GH-024 | Segurança | RBAC inicial para endpoints |
| TASK-0110 | FOUNDATION | Docs | OpenAPI base |
| TASK-0111 | GH-007, GH-008 | Testes | Confiabilidade algoritmo slots |
| TASK-0112 | GH-009 | Testes | Fluxo de reserva happy path |
| TASK-0200 | GH-014, GH-015, GH-033 | Pagamentos | Abstração provider |
| TASK-0201 | GH-014, GH-015 | Pagamentos | Implementação concreta gateway |
| TASK-0202 | GH-014, GH-015, GH-033 | Pagamentos | Modelos Payment/Refund |
| TASK-0203 | GH-014 | Pagamentos | Início transação |
| TASK-0204 | GH-014, GH-015, GH-033 | Pagamentos | Webhook + outbox idempotente |
| TASK-0205 | GH-014, GH-015, GH-033 | Pagamentos | Reconciliação estados |
| TASK-0206 | GH-015 | Pagamentos | Reembolso endpoint |
| TASK-0207 | GH-033 | Pagamentos | Logs consulta |
| TASK-0208 | GH-016, GH-030 | Notificações | Worker lembrete & espera |
| TASK-0209 | GH-016 | Notificações | Template lembrete |
| TASK-0210 | GH-014, GH-015 | Testes | Integração pagamentos |
| TASK-0211 | GH-014, GH-015 | Testes | Idempotência webhooks |
| TASK-0212 | GH-014, GH-015, GH-033 | Observabilidade | Métricas de pagamento |
| TASK-0300 | GH-010, GH-038 | Políticas | Regras cancelamento |
| TASK-0301 | GH-010 | Políticas | Aplicação taxa |
| TASK-0302 | GH-011, GH-032 | Políticas | No-show workflow |
| TASK-0303 | GH-025 | Auditoria | AuditEvent persistido |
| TASK-0304 | GH-019, GH-020, GH-040 | Relatórios | Base agregação ocupação |
| TASK-0305 | GH-019 | Relatórios | Operacionais |
| TASK-0306 | GH-020 | Relatórios | Plataforma |
| TASK-0307 | GH-043 | Scheduling | Ajustar status |
| TASK-0308 | GH-044 | Scheduling | Histórico reservas |
| TASK-0309 | GH-032 | Políticas | Bloqueio no-show |
| TASK-0310 | GH-010, GH-011, GH-032 | Testes | Cobertura limites políticas |
| TASK-0311 | GH-019, GH-020 | Testes | Agregações relatórios |
| TASK-0400 | GH-012, GH-050 | Scheduling Avançado | Waitlist |
| TASK-0401 | GH-013 | Scheduling Avançado | Overbooking controlado |
| TASK-0402 | GH-029 | Scheduling Avançado | Pacote multi-serviço |
| TASK-0403 | GH-028 | Scheduling Avançado | Reagendar |
| TASK-0404 | GH-030 | Notificações | Notificação fila |
| TASK-0405 | GH-017 | Reviews | Avaliar serviço |
| TASK-0406 | GH-018 | Reviews | Moderação |
| TASK-0407 | GH-022 | Fidelidade | Acúmulo pontos |
| TASK-0408 | GH-023, GH-048 | Fidelidade/Promo | Resgate & desconto |
| TASK-0409 | GH-029 | Testes | Transação pacotes |
| TASK-0410 | GH-017, GH-034, GH-035 | Testes | Ranking & filtros avaliações |
| TASK-0411 | GH-022, GH-023 | Testes | Pontos ledger consistente |
| TASK-0500 | GH-024 | Segurança | RBAC refinado |
| TASK-0501 | GH-027 | Compliance | Anonimização PII |
| TASK-0502 | GH-046 | Compliance | Exportar dados |
| TASK-0503 | GH-021, GH-039 | Financeiro | Comissão + regras |
| TASK-0504 | GH-040 | Relatórios | Painel desempenho |
| TASK-0505 | GH-031 | Relatórios | Export CSV |
| TASK-0506 | GH-042 | Busca | Localização |
| TASK-0507 | GH-045 | Observabilidade | Dashboards & alertas |
| TASK-0508 | PER-001 | Performance | Índices críticos |
| TASK-0509 | PER-001 | Performance | Teste carga valida P95 |
| TASK-0510 | SEC-001, SEC-002 | Segurança | Headers + endurecimento |
| TASK-0600 | GH-035 | Busca | Filtro composto |
| TASK-0601 | GH-034 | Reviews | Paginação avaliações |
| TASK-0602 | GH-047 | Entidades | Atualizar dados salão |
| TASK-0603 | GH-048 | Promoções | Desconto promocional |
| TASK-0604 | GH-049 | Scheduling | Cancelamento recepção |
| TASK-0605 | GH-050 | Scheduling | Visualizar fila recepção |
| TASK-0606 | PER-001 | Performance | Cache slots/catalog |
| TASK-0607 | SEC-001..SEC-004 | Segurança | Hardening final |
| TASK-0608 | FOUNDATION | Qualidade | Fechamento dívida técnica |

Critérios de validação automáticos recomendados:

- Cada PR referencia pelo menos 1 TASK e 1 GH issue correspondente.
- Nenhum TASK permanece sem issue (exceto marcados FOUNDATION ou PER/SEC específicos).
- Métrica rastreabilidade: 100% das issues GH-xxx possuem ao menos 1 TASK associado (verificar via script futuro).


