# Índice de Issues

Este documento lista todas as user stories (GH-001 a GH-050), agrupadas por épico e fase sugerida do roadmap, com links para os arquivos locais.

## Épicos

| Épico | Descrição | Issues |
|-------|-----------|--------|
| Auth & Security | Cadastro, login, segurança, rate limiting | GH-001, GH-002, GH-003, GH-026, GH-041 |
| Accounts & Entities | Estruturas de salão, unidade, serviços, profissionais | GH-004, GH-005, GH-006, GH-047 |
| Scheduling Core | Disponibilidade, reserva, agenda, status | GH-007, GH-008, GH-009, GH-043, GH-044, GH-036, GH-037 |
| Policies & Compliance | Cancelamento, no-show, LGPD, anonimização | GH-010, GH-038, GH-032, GH-027, GH-046 |
| Payments & Finance | Pagamentos, reembolsos, logs, comissões, descontos | GH-014, GH-015, GH-033, GH-021, GH-039, GH-048 |
| Notifications | Lembretes e fila de espera | GH-016, GH-030 |
| Reputation & Feedback | Avaliações e moderação | GH-017, GH-018, GH-034, GH-035 |
| Loyalty & Promotions | Pontos, resgate, promo codes | GH-022, GH-023, GH-048 |
| Advanced Scheduling | Fila, overbooking, pacotes, reagendamento | GH-012, GH-013, GH-029, GH-050, GH-028 |
| Reporting & Analytics | Relatórios e métricas | GH-019, GH-020, GH-040, GH-031 |
| Monitoring & Observability | Logs, auditoria, erros | GH-025, GH-045 |
| Search & Discovery | Filtros, localização | GH-042, GH-035 |

## Matriz Fase vs Story

| Fase | Objetivo | Stories Principais |
|------|----------|-------------------|
| Fase 1 | Fundamentos (auth, catálogo, agenda básica) | GH-001, GH-002, GH-003, GH-004, GH-005, GH-006, GH-007, GH-008, GH-009 |
| Fase 2 | Pagamentos & Notificações | GH-014, GH-015, GH-016, GH-010 (taxas no checkout), GH-033 |
| Fase 3 | Políticas, No-show, Relatórios iniciais | GH-011, GH-019, GH-020, GH-038, GH-032, GH-043, GH-044 |
| Fase 4 | Avaliações, Fidelidade inicial, Avanços agenda | GH-012, GH-013, GH-017, GH-018, GH-022, GH-023, GH-029, GH-030, GH-050 |
| Fase 5 | Segurança avançada, Auditoria, Performance | GH-024, GH-025, GH-026, GH-027, GH-041, GH-045, GH-046, GH-039, GH-021, GH-040, GH-031, GH-042 |
| Fase 6 | Expansões & Otimizações | GH-028, GH-035, GH-034, GH-047, GH-048, GH-049 |

## Lista completa

| ID | Título | Épico | Fase | Arquivo |
|----|--------|-------|------|---------|
| GH-001 | Cadastro de cliente | Auth & Security | 1 | [GH-001](GH-001-cadastro-cliente.md) |
| GH-002 | Login e autenticação | Auth & Security | 1 | [GH-002](GH-002-login-autenticacao.md) |
| GH-003 | Recuperação de senha | Auth & Security | 1 | [GH-003](GH-003-recuperacao-senha.md) |
| GH-004 | Cadastro de salão/unidade | Accounts & Entities | 1 | [GH-004](GH-004-cadastro-unidade.md) |
| GH-005 | Cadastro de profissional | Accounts & Entities | 1 | [GH-005](GH-005-cadastro-profissional.md) |
| GH-006 | Configurar catálogo de serviços | Accounts & Entities | 1 | [GH-006](GH-006-config-catalogo-servicos.md) |
| GH-007 | Ajustar disponibilidade profissional | Scheduling Core | 1 | [GH-007](GH-007-ajuste-disponibilidade-profissional.md) |
| GH-008 | Buscar slots disponíveis | Scheduling Core | 1 | [GH-008](GH-008-buscar-slots.md) |
| GH-009 | Reservar serviço | Scheduling Core | 1 | [GH-009](GH-009-reservar-servico.md) |
| GH-010 | Política de cancelamento | Policies & Compliance | 2 | [GH-010](GH-010-politica-cancelamento.md) |
| GH-011 | Marcar no-show | Policies & Compliance | 3 | [GH-011](GH-011-marcar-no-show.md) |
| GH-012 | Fila de espera | Advanced Scheduling | 4 | [GH-012](GH-012-fila-espera.md) |
| GH-013 | Overbooking controlado | Advanced Scheduling | 4 | [GH-013](GH-013-overbooking-controlado.md) |
| GH-014 | Pagamento Pix e cartão | Payments & Finance | 2 | [GH-014](GH-014-pagamento-pix-cartao.md) |
| GH-015 | Reembolso | Payments & Finance | 2 | [GH-015](GH-015-reembolso.md) |
| GH-016 | Notificações de lembrete | Notifications | 2 | [GH-016](GH-016-notificacoes-lembrete.md) |
| GH-017 | Avaliar serviço | Reputation & Feedback | 4 | [GH-017](GH-017-avaliar-servico.md) |
| GH-018 | Moderação de avaliações | Reputation & Feedback | 4 | [GH-018](GH-018-moderacao-avaliacoes.md) |
| GH-019 | Relatórios operacionais | Reporting & Analytics | 3 | [GH-019](GH-019-relatorios-operacionais.md) |
| GH-020 | Relatórios de plataforma | Reporting & Analytics | 3 | [GH-020](GH-020-relatorios-plataforma.md) |
| GH-021 | Comissão profissional | Payments & Finance | 5 | [GH-021](GH-021-comissao-profissional.md) |
| GH-022 | Fidelidade (pontos) | Loyalty & Promotions | 4 | [GH-022](GH-022-fidelidade-pontos.md) |
| GH-023 | Resgate de pontos | Loyalty & Promotions | 4 | [GH-023](GH-023-resgate-pontos.md) |
| GH-024 | Gestão de usuários e permissões | Auth & Security | 5 | [GH-024](GH-024-gestao-usuarios-permissoes.md) |
| GH-025 | Auditoria de eventos | Monitoring & Observability | 5 | [GH-025](GH-025-auditoria-eventos.md) |
| GH-026 | Rate limiting de login | Auth & Security | 5 | [GH-026](GH-026-rate-limiting-login.md) |
| GH-027 | Anonimização de dados | Policies & Compliance | 5 | [GH-027](GH-027-anonimizacao-dados.md) |
| GH-028 | Reagendar reserva | Advanced Scheduling | 6 | [GH-028](GH-028-reagendar-reserva.md) |
| GH-029 | Pacote multi-serviço | Advanced Scheduling | 4 | [GH-029](GH-029-pacote-multi-servico.md) |
| GH-030 | Notificação fila de espera | Notifications | 4 | [GH-030](GH-030-notificacao-fila-espera.md) |
| GH-031 | Exportação relatórios CSV | Reporting & Analytics | 5 | [GH-031](GH-031-exportacao-relatorios-csv.md) |
| GH-032 | Bloqueio por no-shows | Policies & Compliance | 3 | [GH-032](GH-032-bloqueio-no-shows.md) |
| GH-033 | Logs de pagamento | Payments & Finance | 2 | [GH-033](GH-033-logs-pagamento.md) |
| GH-034 | Busca por avaliações | Reputation & Feedback | 6 | [GH-034](GH-034-busca-avaliacoes.md) |
| GH-035 | Filtro preço e avaliação | Reputation & Feedback / Search | 6 | [GH-035](GH-035-filtro-preco-avaliacao.md) |
| GH-036 | Visualizar agenda própria | Scheduling Core | 5 | [GH-036](GH-036-agenda-propria-profissional.md) |
| GH-037 | Agenda global unidade | Scheduling Core | 5 | [GH-037](GH-037-agenda-global-unidade.md) |
| GH-038 | Configurar política cancelamento | Policies & Compliance | 3 | [GH-038](GH-038-config-politica-cancelamento.md) |
| GH-039 | Definir comissões | Payments & Finance | 5 | [GH-039](GH-039-definir-comissoes.md) |
| GH-040 | Painel desempenho profissional | Reporting & Analytics | 5 | [GH-040](GH-040-painel-desempenho-profissional.md) |
| GH-041 | Sessão e logout seguro | Auth & Security | 5 | [GH-041](GH-041-sessao-logout-seguro.md) |
| GH-042 | Pesquisa por localização | Search & Discovery | 5 | [GH-042](GH-042-pesquisa-localizacao.md) |
| GH-043 | Ajustar status de reserva | Scheduling Core | 3 | [GH-043](GH-043-ajustar-status-reserva.md) |
| GH-044 | Histórico de reservas cliente | Scheduling Core | 3 | [GH-044](GH-044-historico-reservas-cliente.md) |
| GH-045 | Monitoramento de erros | Monitoring & Observability | 5 | [GH-045](GH-045-monitoramento-erros.md) |
| GH-046 | Exportar dados pessoais | Policies & Compliance | 5 | [GH-046](GH-046-exportar-dados-pessoais.md) |
| GH-047 | Atualizar dados do salão | Accounts & Entities | 6 | [GH-047](GH-047-atualizar-dados-salao.md) |
| GH-048 | Aplicar desconto promocional | Payments & Finance / Loyalty | 6 | [GH-048](GH-048-desconto-promocional.md) |
| GH-049 | Cancelamento pela recepção | Scheduling Core | 6 | [GH-049](GH-049-cancelamento-recepcao.md) |
| GH-050 | Visualizar fila de espera | Advanced Scheduling | 4 | [GH-050](GH-050-visualizar-fila-espera.md) |

## Script de criação (gh CLI)

Arquivo gerado: `scripts/create_github_issues.ps1` com comandos para cada issue. Edite a variável `$Repo` antes de executar.

gh issue create --repo romanzini/esalao_app.git --title "GH-001 Cadastro de cliente" --body-file ".\\issues\\GH-001-cadastro-cliente.md" --label "feature,auth,backend"
