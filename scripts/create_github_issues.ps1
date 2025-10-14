Param(
    [string]$Repo = "<owner>/<repo>"
)

if ($Repo -eq "<owner>/<repo>") {
    Write-Host "Defina o parâmetro -Repo (ex.: org/esalao_app) antes de executar." -ForegroundColor Yellow
    return
}

$basePath = Join-Path $PSScriptRoot "..\issues"

$issues = @(
    'GH-001-cadastro-cliente.md','GH-002-login-autenticacao.md','GH-003-recuperacao-senha.md','GH-004-cadastro-unidade.md','GH-005-cadastro-profissional.md',
    'GH-006-config-catalogo-servicos.md','GH-007-ajuste-disponibilidade-profissional.md','GH-008-buscar-slots.md','GH-009-reservar-servico.md','GH-010-politica-cancelamento.md',
    'GH-011-marcar-no-show.md','GH-012-fila-espera.md','GH-013-overbooking-controlado.md','GH-014-pagamento-pix-cartao.md','GH-015-reembolso.md',
    'GH-016-notificacoes-lembrete.md','GH-017-avaliar-servico.md','GH-018-moderacao-avaliacoes.md','GH-019-relatorios-operacionais.md','GH-020-relatorios-plataforma.md',
    'GH-021-comissao-profissional.md','GH-022-fidelidade-pontos.md','GH-023-resgate-pontos.md','GH-024-gestao-usuarios-permissoes.md','GH-025-auditoria-eventos.md',
    'GH-026-rate-limiting-login.md','GH-027-anonimizacao-dados.md','GH-028-reagendar-reserva.md','GH-029-pacote-multi-servico.md','GH-030-notificacao-fila-espera.md',
    'GH-031-exportacao-relatorios-csv.md','GH-032-bloqueio-no-shows.md','GH-033-logs-pagamento.md','GH-034-busca-avaliacoes.md','GH-035-filtro-preco-avaliacao.md',
    'GH-036-agenda-propria-profissional.md','GH-037-agenda-global-unidade.md','GH-038-config-politica-cancelamento.md','GH-039-definir-comissoes.md','GH-040-painel-desempenho-profissional.md',
    'GH-041-sessao-logout-seguro.md','GH-042-pesquisa-localizacao.md','GH-043-ajustar-status-reserva.md','GH-044-historico-reservas-cliente.md','GH-045-monitoramento-erros.md',
    'GH-046-exportar-dados-pessoais.md','GH-047-atualizar-dados-salao.md','GH-048-desconto-promocional.md','GH-049-cancelamento-recepcao.md','GH-050-visualizar-fila-espera.md'
)

foreach ($file in $issues) {
    $path = Join-Path $basePath $file
    if (-Not (Test-Path $path)) { Write-Warning "Arquivo não encontrado: $path"; continue }
    $id = ($file -split '-')[0]
    $titleLine = (Get-Content $path | Select-String -Pattern "^# ") | Select-Object -First 1
    if ($null -eq $titleLine) { Write-Warning "Título não encontrado em $file"; continue }
    $title = $titleLine.ToString().Substring(2)
    Write-Host "Criando issue: $title" -ForegroundColor Cyan
    gh issue create --repo $Repo --title $title --body-file $path --label "auto-import" | Out-Null
}

Write-Host "Processo concluído." -ForegroundColor Green
