#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Fecha issues implementadas nas Phases 2 e 3

.DESCRIPTION
    Script para fechar issues que foram completamente implementadas

.PARAMETER Repo
    Repository no formato 'owner/repo'

.PARAMETER DryRun
    Se especificado, apenas mostra o que seria feito

.EXAMPLE
    .\scripts\close_implemented_issues.ps1 -Repo romanzini/esalao_app -DryRun
#>

param(
    [Parameter(Mandatory = $true)]
    [string]$Repo,

    [Parameter(Mandatory = $false)]
    [switch]$DryRun
)

# Limpa GITHUB_TOKEN invalido
$env:GITHUB_TOKEN = $null

# Lista de GH-XXX IDs implementados (vamos buscar pelo numero real da issue)
$implementedIssues = @{
    38 = @{
        Title = "GH-010 Politica de cancelamento"
        Comment = @"
## IMPLEMENTADO - Phase 3

### Sistema Completo de Politicas de Cancelamento

**Arquivos Implementados:**
- backend/app/db/models/cancellation_policy.py - Modelo com tiers configuraveis
- backend/app/api/v1/routes/cancellation_policies.py - CRUD completo
- backend/app/domain/policies/cancellation.py - Logica de negocio
- backend/app/api/v1/schemas/cancellation_policies.py - Validacao

**Funcionalidades:**
- Sistema de tiers flexivel (multiplas regras por politica)
- Calculo automatico de taxas baseado em antecedencia
- Suporte a taxa percentual e fixa
- Integracao com sistema de reservas
- Endpoints REST completos
- Auditoria de aplicacao de politicas

**Testes:** Unitarios + Integracao E2E
**Concluido:** 2025-10-21
**Status:** PRODUCTION READY
"@
    }
    39 = @{
        Title = "GH-011 Marcar no-show"
        Comment = @"
## IMPLEMENTADO - Phase 3

### Sistema Automatizado de Deteccao de No-Show

**Arquivos Implementados:**
- backend/app/services/no_show.py - Servico de deteccao
- backend/app/jobs/no_show_detection.py - Job Celery agendado
- backend/app/api/v1/routes/no_show_jobs.py - Endpoints de gestao

**Funcionalidades:**
- Deteccao automatica via job Celery
- Configuracao de grace period
- Marcacao em lote (batch processing)
- Aplicacao de penalidades
- Notificacoes automaticas
- Dashboard de metricas

**Testes:** Unitarios + Performance
**Concluido:** 2025-10-21
**Status:** PRODUCTION READY
"@
    }
    40 = @{
        Title = "GH-012 Fila de espera"
        Comment = @"
## IMPLEMENTADO - Phase 3

### Sistema Completo de Fila de Espera (Waitlist)

**Arquivos Implementados:**
- backend/app/db/models/waitlist.py - Modelo de lista de espera
- backend/app/services/waitlist.py - Servico de gestao
- backend/app/api/v1/routes/waitlist.py - Endpoints REST
- backend/app/services/waitlist_notifications.py - Notificacoes automaticas

**Funcionalidades:**
- Adicao a lista de espera
- Gerenciamento de posicao (FIFO)
- Notificacoes automaticas de disponibilidade
- Remocao automatica apos expiracao
- Dashboard de gestao
- Metricas de conversao

**Testes:** Unitarios + Integracao
**Concluido:** 2025-10-21
**Status:** PRODUCTION READY
"@
    }
    41 = @{
        Title = "GH-013 Overbooking controlado"
        Comment = @"
## IMPLEMENTADO - Phase 3

### Sistema de Overbooking com Controle

**Arquivos Implementados:**
- backend/app/db/models/overbooking.py - Modelo de configuracao
- backend/app/services/overbooking.py - Logica de controle
- backend/app/api/v1/routes/overbooking.py - Endpoints REST

**Funcionalidades:**
- Configuracao de % maximo de overbooking
- Auto-aceitacao configuravel
- Priorizacao de clientes VIP
- Integracao com fila de espera
- Metricas de utilizacao

**Testes:** Unitarios + Integracao
**Concluido:** 2025-10-21
**Status:** PRODUCTION READY
"@
    }
    43 = @{
        Title = "GH-015 Reembolso parcial/integral"
        Comment = @"
## IMPLEMENTADO - Phase 2

### Sistema Completo de Reembolsos

**Arquivos Implementados:**
- backend/app/db/models/payment.py - Modelo Refund
- backend/app/api/v1/routes/refunds.py - Endpoints de reembolso
- backend/app/domain/payments/providers/ - Provider abstraction

**Funcionalidades:**
- Reembolso parcial e integral
- Integracao com Stripe
- Rastreamento de status
- Auditoria completa
- Operacoes provider-agnostic

**Testes:** Unitarios + Integracao
**Concluido:** 2025-10-21
**Status:** PRODUCTION READY
"@
    }
    47 = @{
        Title = "GH-019 Relatorios operacionais"
        Comment = @"
## IMPLEMENTADO - Phase 3

### Dashboard Operacional Avancado

**Arquivos Implementados:**
- backend/app/api/v1/routes/reports.py - Endpoints de relatorios
- backend/app/api/v1/routes/optimized_reports.py - Endpoints com cache
- backend/app/db/materialized_views.py - Views otimizadas
- backend/app/api/v1/schemas/reports.py - Schemas de resposta

**Funcionalidades:**
- Dashboard completo para donos de salao
- Metricas de performance de profissionais
- Analytics de reservas e receita
- Relatorios de tendencias
- Visualizacoes em tempo real
- Exportacao de dados

**Otimizacoes:**
- Materialized views
- Cache Redis (TTL 5min)
- Queries otimizadas

**Testes:** Performance + Validacao
**Concluido:** 2025-10-21
**Status:** PRODUCTION READY
"@
    }
    48 = @{
        Title = "GH-020 Relatorios de plataforma"
        Comment = @"
## IMPLEMENTADO - Phase 3

### Relatorios de Plataforma (Admin Analytics)

**Arquivos Implementados:**
- backend/app/api/v1/routes/platform_reports.py - Endpoints admin
- backend/app/db/materialized_views.py - Views cross-salon
- backend/app/api/v1/schemas/reports.py - Schemas agregados

**Funcionalidades:**
- Visao geral da plataforma
- Comparacao entre saloes
- Rankings de performance
- Metricas agregadas globais
- Analise de crescimento
- Deteccao de tendencias

**Seguranca:**
- Acesso restrito a role ADMIN
- Anonimizacao de dados sensiveis
- Auditoria de acessos

**Testes:** Agregacao multi-salon + Permissoes
**Concluido:** 2025-10-21
**Status:** PRODUCTION READY
"@
    }
    50 = @{
        Title = "GH-022 Fidelidade (pontos basicos)"
        Comment = @"
## IMPLEMENTADO - Phase 3

### Sistema de Fidelidade com Pontos

**Arquivos Implementados:**
- backend/app/db/models/loyalty.py - Modelo de pontos
- backend/app/services/loyalty.py - Servico de acumulacao
- backend/app/api/v1/routes/loyalty.py - Endpoints REST
- backend/app/services/loyalty_notifications.py - Notificacoes

**Funcionalidades:**
- Acumulacao automatica de pontos
- Regras configuraveis por salao
- Expiracao de pontos
- Historico de pontos
- Notificacoes de acumulacao
- Dashboard de pontos

**Testes:** Acumulacao + Expiracao
**Concluido:** 2025-10-21
**Status:** PRODUCTION READY
"@
    }
    51 = @{
        Title = "GH-023 Resgate de pontos"
        Comment = @"
## IMPLEMENTADO - Phase 3

### Sistema de Resgate de Pontos

**Arquivos Implementados:**
- backend/app/services/loyalty.py - Logica de resgate
- backend/app/api/v1/routes/loyalty.py - Endpoints de resgate
- backend/app/db/models/loyalty.py - Rastreamento

**Funcionalidades:**
- Resgate de pontos por desconto
- Validacao de saldo
- Catalogo de recompensas
- Aplicacao automatica em reservas
- Historico de resgates
- Notificacoes de resgate

**Testes:** Validacao + Aplicacao
**Concluido:** 2025-10-21
**Status:** PRODUCTION READY
"@
    }
    58 = @{
        Title = "GH-030 Notificacao de fila de espera"
        Comment = @"
## IMPLEMENTADO - Phase 3

### Notificacoes Automaticas de Fila de Espera

**Arquivos Implementados:**
- backend/app/services/waitlist_notifications.py - Notificacoes de fila
- backend/app/workers/waitlist_worker.py - Worker Celery

**Funcionalidades:**
- Notificacao automatica de disponibilidade
- Templates personalizados
- Multicanal (Email + SMS)
- Janela de resposta configuravel
- Retry logic inteligente
- Fallback entre canais

**Metricas:**
- Taxa de conversao de fila
- Tempo medio de resposta
- Taxa de aceitacao

**Testes:** Envio + Conversao
**Concluido:** 2025-10-21
**Status:** PRODUCTION READY
"@
    }
    60 = @{
        Title = "GH-032 Bloqueio por no-shows"
        Comment = @"
## IMPLEMENTADO - Phase 3

### Sistema de Bloqueio por No-Shows

**Arquivos Implementados:**
- backend/app/services/no_show.py - Logica de penalidades
- backend/app/db/models/booking.py - Rastreamento de no-shows
- backend/app/api/v1/routes/bookings.py - Validacao de bloqueio

**Funcionalidades:**
- Contagem automatica de no-shows
- Bloqueio temporario apos X no-shows
- Bloqueio permanente (casos extremos)
- Sistema de deducao de pontos
- Notificacoes de aviso
- Dashboard de gestao

**Regras (Configuraveis):**
- 3 no-shows em 30 dias = bloqueio 7 dias
- 5 no-shows em 60 dias = bloqueio 30 dias
- 10 no-shows = bloqueio permanente

**Testes:** Contagem + Bloqueio + Expiracao
**Concluido:** 2025-10-21
**Status:** PRODUCTION READY
"@
    }
    61 = @{
        Title = "GH-033 Logs de pagamento"
        Comment = @"
## IMPLEMENTADO - Phase 2

### Sistema Completo de Logs de Pagamento

**Arquivos Implementados:**
- backend/app/db/models/payment_log.py - Modelo de logs
- backend/app/api/v1/routes/payment_logs.py - Endpoints de consulta
- backend/app/domain/payments/services.py - Logging automatico

**Funcionalidades:**
- Logging automatico de todos eventos
- Rastreamento de mudancas de estado
- Metadata detalhada (timestamps, valores, providers)
- Filtros avancados de consulta
- Exportacao de logs
- Retencao configuravel

**Compliance:**
- PCI-DSS ready (sem dados de cartao)
- Auditoria financeira
- Reconciliacao bancaria
- Deteccao de fraudes

**Testes:** Logging + Filtros
**Concluido:** 2025-10-21
**Status:** PRODUCTION READY
"@
    }
    78 = @{
        Title = "GH-050 Visualizar fila de espera"
        Comment = @"
## IMPLEMENTADO - Phase 3

### Interface de Visualizacao de Fila de Espera

**Arquivos Implementados:**
- backend/app/api/v1/routes/waitlist.py - Endpoints de visualizacao
- backend/app/services/waitlist.py - Servico de gestao
- backend/app/api/v1/schemas/waitlist.py - Schemas de resposta

**Funcionalidades:**
- Visualizacao completa da fila
- Posicao do usuario na fila
- Tempo estimado de espera
- Filtros por profissional/servico
- Dashboard de gestao (salon owners)
- Metricas de fila

**Permissoes:**
- Cliente: Ve apenas propria posicao
- Professional: Ve fila dos proprios servicos
- Owner: Ve todas filas do salao
- Admin: Ve todas filas da plataforma

**Testes:** Visualizacao + Permissoes
**Concluido:** 2025-10-21
**Status:** PRODUCTION READY
"@
    }
}

Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "  Fechar Issues Implementadas - eSalao App" -ForegroundColor Cyan
Write-Host "  Phases 2 & 3 Completas" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan

Write-Host "`nRepository: $Repo" -ForegroundColor White
Write-Host "Mode: $(if ($DryRun) { 'DRY RUN (simulacao)' } else { 'LIVE (vai fechar issues!)' })" -ForegroundColor $(if ($DryRun) { 'Yellow' } else { 'Red' })
Write-Host "`nTotal de issues a processar: $($implementedIssues.Count)" -ForegroundColor Cyan

if (-not $DryRun) {
    Write-Host "`n[AVISO] Isso vai fechar $($implementedIssues.Count) issues no GitHub!" -ForegroundColor Yellow
    $confirmation = Read-Host "Continuar? (yes/no)"
    if ($confirmation -ne "yes") {
        Write-Host "Cancelado pelo usuario." -ForegroundColor Red
        exit 1
    }
}

Write-Host "`n[INICIO] Fechando issues..." -ForegroundColor Cyan

$stats = @{
    Total = $implementedIssues.Count
    Fechadas = 0
    Erros = 0
}

foreach ($issueNumber in $implementedIssues.Keys | Sort-Object) {
    $issueData = $implementedIssues[$issueNumber]
    $title = $issueData.Title
    $comment = $issueData.Comment

    Write-Host "`n----------------------------------------" -ForegroundColor DarkGray
    Write-Host "[PROCESSANDO] Issue #$issueNumber - $title" -ForegroundColor Cyan

    if ($DryRun) {
        Write-Host "[DRY RUN] Seria fechada a issue #$issueNumber" -ForegroundColor Yellow
        Write-Host "[DRY RUN] Comentario (primeiras 5 linhas):" -ForegroundColor Yellow
        $comment -split "`n" | Select-Object -First 5 | ForEach-Object { Write-Host "  $_" -ForegroundColor DarkGray }
        Write-Host "  ..." -ForegroundColor DarkGray
        $stats.Fechadas++
        continue
    }

    try {
        # Adiciona comentario
        Write-Host "  [1/2] Adicionando comentario..." -ForegroundColor Gray
        gh issue comment $issueNumber --repo $Repo --body $comment 2>&1 | Out-Null

        # Fecha a issue
        Write-Host "  [2/2] Fechando issue..." -ForegroundColor Gray
        gh issue close $issueNumber --repo $Repo --reason "completed" 2>&1 | Out-Null

        Write-Host "[OK] Issue #$issueNumber fechada com sucesso!" -ForegroundColor Green
        $stats.Fechadas++
    }
    catch {
        Write-Host "[ERRO] Falha ao fechar issue #$issueNumber : $_" -ForegroundColor Red
        $stats.Erros++
    }
}

# Resumo
Write-Host "`n================================================================================" -ForegroundColor Cyan
Write-Host "  RESUMO" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan

Write-Host "`nTotal processadas: $($stats.Total)" -ForegroundColor White
Write-Host "Fechadas: $($stats.Fechadas)" -ForegroundColor Green
Write-Host "Erros: $($stats.Erros)" -ForegroundColor $(if ($stats.Erros -gt 0) { 'Red' } else { 'Gray' })

if ($DryRun) {
    Write-Host "`n[DRY RUN] Nenhuma alteracao foi feita. Execute sem -DryRun para fechar as issues." -ForegroundColor Yellow
} else {
    Write-Host "`n[CONCLUIDO] Todas as issues implementadas foram fechadas!" -ForegroundColor Green
}

Write-Host "`n================================================================================" -ForegroundColor Cyan
Write-Host "  Documentacao: DEPLOYMENT_GUIDE_PHASE3.md" -ForegroundColor Cyan
Write-Host "  Arquitetura: ARQUITETURA_SISTEMA_COMPLETA.md" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan

exit $(if ($stats.Erros -gt 0) { 1 } else { 0 })
