Param(
    [Parameter(Mandatory=$true)][string]$Repo,
    [switch]$DryRun
)

# Sanitiza o parametro de repositorio removendo barras invertidas/aspas acidentais
# Causa do erro 404 observado: comando foi executado como -Repo \"romanzini/esalao_app\" gerando valor literal com backslashes
# que o gh converteu em caminho /repos/\romanzini/esalao_app\ e a API retornou 404.
$originalRepo = $Repo
# Remove caracteres indesejados (\\ / ' ") no início e no fim sem usar regex complexa
function Remove-EdgeChars {
    param([string]$value)
    if (-not $value) { return $value }
    $chars = @('\\','/','\"', "'")
    $changed = $true
    while ($changed) {
        $changed = $false
        foreach ($c in $chars) {
            if ($value.StartsWith($c)) { $value = $value.Substring(1); $changed = $true }
            if ($value.EndsWith($c)) { $value = $value.Substring(0, $value.Length-1); $changed = $true }
        }
    }
    return $value
}
$Repo = Remove-EdgeChars -value $Repo

if ($Repo -ne $originalRepo) {
    Write-Host "[AVISO] -Repo sanitizado de '$originalRepo' para '$Repo'" -ForegroundColor Yellow
}

if ($Repo -notmatch '^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$') {
    Write-Host "[ERRO] Valor de -Repo invalido: '$Repo'. Use o formato owner/repo (ex: romanzini/esalao_app)." -ForegroundColor Red
    return
}

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Host "gh CLI não encontrado." -ForegroundColor Red; return
}

$labels = @(
    # Labels base (usadas nos arquivos de issues)
    @{ name = 'feature'; color = '0e8a16'; description='Nova funcionalidade'; },
    @{ name = 'backend'; color = '1d76db'; description='Backend/API'; },
    @{ name = 'frontend'; color = '5319e7'; description='Frontend/UI'; },
    @{ name = 'auth'; color = 'fbca04'; description='Autenticacao e autorizacao'; },
    @{ name = 'payment'; color = 'b60205'; description='Pagamentos'; },
    @{ name = 'payments'; color = 'b60205'; description='Pagamentos'; },
    @{ name = 'notification'; color = 'd93f0b'; description='Notificacoes'; },
    @{ name = 'notifications'; color = 'd93f0b'; description='Notificacoes'; },
    @{ name = 'report'; color = '0052cc'; description='Relatorios e analytics'; },
    @{ name = 'security'; color = 'd73a4a'; description='Seguranca'; },
    @{ name = 'compliance'; color = 'fef2c0'; description='Conformidade/LGPD'; },
    @{ name = 'performance'; color = 'bfdadc'; description='Performance e otimizacao'; },
    @{ name = 'analytics'; color = '0052cc'; description='Analytics e relatorios'; },
    @{ name = 'audit'; color = '6e7781'; description='Auditoria'; },
    @{ name = 'catalog'; color = '1d76db'; description='Catalogo de servicos'; },
    @{ name = 'finance'; color = 'b60205'; description='Financeiro'; },
    @{ name = 'loyalty'; color = '5319e7'; description='Fidelidade'; },
    @{ name = 'moderation'; color = 'fbca04'; description='Moderacao'; },
    @{ name = 'observability'; color = 'f9d0c4'; description='Observabilidade'; },
    @{ name = 'policy'; color = 'fef2c0'; description='Politicas'; },
    @{ name = 'pricing'; color = 'b60205'; description='Precificacao'; },
    @{ name = 'reviews'; color = '0e8a16'; description='Avaliacoes'; },
    @{ name = 'scheduling'; color = '1d76db'; description='Agendamento'; },
    @{ name = 'search'; color = '0366d6'; description='Busca e descoberta'; },
    # Label de automacao
    @{ name = 'auto-import'; color = '6e7781'; description='Criado automaticamente via script de import'; },
    # Labels de epicos (versões com hífen simples)
    @{ name = 'epic:auth-security'; color='0e8a16'; description='Epico Auth & Security'; },
    @{ name = 'epic:accounts-entities'; color='5319e7'; description='Epico Accounts & Entities'; },
    @{ name = 'epic:scheduling-core'; color='1d76db'; description='Epico Scheduling Core'; },
    @{ name = 'epic:policies-compliance'; color='fbca04'; description='Epico Policies & Compliance'; },
    @{ name = 'epic:payments-finance'; color='b60205'; description='Epico Payments & Finance'; },
    @{ name = 'epic:notifications'; color='d93f0b'; description='Epico Notifications'; },
    # Cor anterior 'cfm312' era invalida (hexadecimal exige [0-9a-f]); substituida por 'cf1312'
    @{ name = 'epic:reputation-feedback'; color='cf1312'; description='Epico Reputation & Feedback'; },
    @{ name = 'epic:loyalty-promotions'; color='5319e7'; description='Epico Loyalty & Promotions'; },
    @{ name = 'epic:advanced-scheduling'; color='0052cc'; description='Epico Advanced Scheduling'; },
    @{ name = 'epic:reporting-analytics'; color='5319e7'; description='Epico Reporting & Analytics'; },
    @{ name = 'epic:monitoring-observability'; color='f9d0c4'; description='Epico Monitoring & Observability'; },
    @{ name = 'epic:search-discovery'; color='0366d6'; description='Epico Search & Discovery'; },
    # Labels de epicos (versões com -and- geradas pelo slug)
    @{ name = 'epic:auth-and-security'; color='0e8a16'; description='Epico Auth & Security'; },
    @{ name = 'epic:accounts-and-entities'; color='5319e7'; description='Epico Accounts & Entities'; },
    @{ name = 'epic:policies-and-compliance'; color='fbca04'; description='Epico Policies & Compliance'; },
    @{ name = 'epic:payments-and-finance'; color='b60205'; description='Epico Payments & Finance'; },
    @{ name = 'epic:reputation-and-feedback'; color='cf1312'; description='Epico Reputation & Feedback'; },
    @{ name = 'epic:loyalty-and-promotions'; color='5319e7'; description='Epico Loyalty & Promotions'; },
    @{ name = 'epic:reporting-and-analytics'; color='5319e7'; description='Epico Reporting & Analytics'; },
    @{ name = 'epic:monitoring-and-observability'; color='f9d0c4'; description='Epico Monitoring & Observability'; },
    @{ name = 'epic:search-and-discovery'; color='0366d6'; description='Epico Search & Discovery'; },
    @{ name = 'phase:0'; color='c2e0c6'; description='Fase 0 Fundacoes'; },
    @{ name = 'phase:1'; color='c2e0c6'; description='Fase 1 Fundamentos'; },
    @{ name = 'phase:2'; color='bfdadc'; description='Fase 2 Pagamentos & Notificacoes'; },
    @{ name = 'phase:3'; color='c5def5'; description='Fase 3 Politicas & Relatorios'; },
    @{ name = 'phase:4'; color='fef2c0'; description='Fase 4 Agenda Avancada & Fidelidade'; },
    @{ name = 'phase:5'; color='f9d0c4'; description='Fase 5 Seguranca & Auditoria'; },
    @{ name = 'phase:6'; color='d4c5f9'; description='Fase 6 Expansoes & Otimizacoes'; }
)

foreach ($l in $labels) {
    $exists = gh label list --repo $Repo --search $l.name --limit 1 --json name 2>$null | ConvertFrom-Json | Where-Object { $_.name -eq $l.name }
    if ($exists) {
        Write-Host "Atualizando label: $($l.name)" -ForegroundColor Yellow
        if (-not $DryRun) { gh label edit $l.name --repo $Repo --color $l.color --description $l.description | Out-Null }
    } else {
        Write-Host "Criando label: $($l.name)" -ForegroundColor Green
        if (-not $DryRun) { gh label create $l.name --repo $Repo --color $l.color --description $l.description | Out-Null }
    }
}

Write-Host "Labels processadas." -ForegroundColor Cyan
