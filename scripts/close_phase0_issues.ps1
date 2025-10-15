# Fecha issues do GitHub que foram implementadas na Phase 0

param(
    [string]$Repo = "romanzini/esalao_app"
)

Write-Host "=== Fechando Issues da Phase 0 ===" -ForegroundColor Cyan
Write-Host ""

# GH-026 Rate limiting de login
Write-Host "Fechando #54 - GH-026 Rate limiting de login..." -ForegroundColor Yellow
gh issue close 54 --repo $Repo --comment "Fechada automaticamente - Implementado rate limiting em TASK-0011 (Phase 0). Configurado Slowapi com Redis storage para protecao contra brute force de login e outras rotas criticas. Arquivo: backend/app/core/rate_limit.py. Para mais detalhes, consulte PHASE_0_SUMMARY.md"
if ($LASTEXITCODE -eq 0) {
    Write-Host "  Sucesso!" -ForegroundColor Green
}
Write-Host ""

# GH-025 Auditoria de eventos
Write-Host "Fechando #53 - GH-025 Auditoria de eventos..." -ForegroundColor Yellow
gh issue close 53 --repo $Repo --comment "Parcialmente implementado na Phase 0. TASK-0009: Configurado OpenTelemetry para tracing distribuido. TASK-0008: Implementado logging estruturado com Structlog (JSON). Arquivos: backend/app/core/tracing.py, backend/app/core/logging.py. Framework de auditoria de eventos especificos do negocio sera implementado em fases posteriores. Para mais detalhes, consulte PHASE_0_SUMMARY.md"
if ($LASTEXITCODE -eq 0) {
    Write-Host "  Sucesso!" -ForegroundColor Green
}
Write-Host ""

Write-Host "=== Concluido ===" -ForegroundColor Cyan

