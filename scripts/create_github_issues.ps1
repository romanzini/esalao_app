<#+
.SYNOPSIS
    Cria issues no GitHub a partir dos arquivos em /issues com metadados.

.DESCRIPTION
    Descobre todos arquivos GH-*.md em /issues, lê bloco HTML de metadados (ID, Epic, Phase),
    compõe labels: labels base do arquivo + auto-import + epic:<slug> + phase:<n>.
    Suporta DryRun para visualização, skip se issue já existe (opcional via flag).

.EXAMPLE
    pwsh ./scripts/create_github_issues.ps1 -Repo org/projeto -DryRun

.EXAMPLE
    pwsh ./scripts/create_github_issues.ps1 -Repo org/projeto -IncludeFilter "GH-0(0[1-5]|1[0-2])"

#>
Param(
    [Parameter(Mandatory=$true)][string]$Repo,
    [switch]$DryRun,
    [string]$IncludeFilter,
    [switch]$SkipExisting
)

# Sanitização preventiva do -Repo (remove barras/aspas acidentais nas extremidades)
function Remove-EdgeChars {
    param([string]$value)
    if (-not $value) { return $value }
    $chars = @('\\','/','"', "'")
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
$originalRepo = $Repo
$Repo = Remove-EdgeChars -value $Repo
if ($Repo -ne $originalRepo) { Write-Host "[AVISO] -Repo sanitizado de '$originalRepo' para '$Repo'" -ForegroundColor Yellow }

if ([string]::IsNullOrWhiteSpace($Repo) -or $Repo -like '*<owner>*') {
    Write-Host "Forneça -Repo ex.: org/esalao_app" -ForegroundColor Yellow; return }

if ($Repo -notmatch '^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$') {
    Write-Host "[ERRO] Valor de -Repo invalido: '$Repo'. Use o formato owner/repo (ex: romanzini/esalao_app)." -ForegroundColor Red
    return
}

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Host "gh CLI não encontrado no PATH." -ForegroundColor Red
    return
}

$basePath = Join-Path $PSScriptRoot '..' | Join-Path -ChildPath 'issues'
if (-not (Test-Path $basePath)) { Write-Host "Diretório issues não encontrado: $basePath" -ForegroundColor Red; return }

function Get-Meta {
    param([string]$Raw)
    $meta = @{}
    $lines = $Raw -split "`n"
    if ($lines.Length -gt 0 -and $lines[0].Trim() -eq '<!--') {
        for ($i=1; $i -lt $lines.Length; $i++) {
            $l = $lines[$i].Trim()
            if ($l -eq '-->') { break }
            if ($l -match '^(?<k>[^:]+):\s*(?<v>.+)$') {
                $meta[$Matches.k.Trim()] = $Matches.v.Trim()
            }
        }
    }
    return $meta
}

function New-Slug($text) {
    ($text.ToLower() -replace '&',' and ' -replace '[^a-z0-9]+','-').Trim('-')
}

function Get-BaseLabels($raw) {
    $labels = @()
    $capture = $false
    foreach ($ln in ($raw -split "`n")) {
        if ($ln.Trim() -eq '## Labels') { $capture = $true; continue }
        if ($capture) {
            $t = $ln.Trim()
            if ($t -eq '') { continue }
            if ($t -match '^# ') { break }
            $labels = ($t -split ',') | ForEach-Object { $_.Trim() } | Where-Object { $_ }
            break
        }
    }
    return $labels
}

function Issue-Exists($repo,$title) {
    # Consulta rápida; limita a 1 resultado
    $json = gh issue list --repo $repo --search $("title:'$title'") --state all --json title --limit 1 2>$null | ConvertFrom-Json
    if ($null -eq $json) { return $false }
    return ($json | Where-Object { $_.title -eq $title }) -ne $null
}

$files = Get-ChildItem -Path $basePath -File -Filter 'GH-*.md' | Sort-Object Name
if ($IncludeFilter) {
    try {
        # Testa padrão antes de aplicar
        '' -match $IncludeFilter | Out-Null
        $files = $files | Where-Object { $_.Name -match $IncludeFilter }
    } catch {
        Write-Host "[ERRO] IncludeFilter regex invalida: $IncludeFilter" -ForegroundColor Red
        Write-Host "Dica: Para IDs 001-005 use: ^GH-00[1-5]- ou ^GH-001-" -ForegroundColor Yellow
        Write-Host "      Formato dos arquivos: GH-001-descricao.md, GH-002-descricao.md, etc." -ForegroundColor Yellow
        return
    }
}
if (-not $files) { Write-Host "Nenhum arquivo correspondente encontrado." -ForegroundColor Yellow; return }

Write-Host "Processando $($files.Count) arquivo(s)..." -ForegroundColor Cyan

$created = 0; $skipped = 0
foreach ($f in $files) {
    $raw = Get-Content $f.FullName -Raw
    $meta = Get-Meta -Raw $raw
    # Remove bloco de comentário HTML completo e pega primeiro heading real não vazio
    $content = $raw -replace '(?s)<!--.*?-->', ''
    $titleLine = ($content -split "`n" | Where-Object { $_ -match '^# \S' } | Select-Object -First 1)
    if (-not $titleLine) { Write-Warning "Título não encontrado em $($f.Name)"; continue }
    $title = $titleLine.Substring(2).Trim()

    if ($SkipExisting -and (Issue-Exists -repo $Repo -title $title)) {
        Write-Host "Skip (já existe): $title" -ForegroundColor DarkYellow
        $skipped++
        continue
    }

    $labels = New-Object System.Collections.Generic.List[string]
    (Get-BaseLabels -raw $raw) | ForEach-Object { if (-not [string]::IsNullOrWhiteSpace($_)) { $labels.Add($_) } }
    if (-not $labels.Contains('auto-import')) { $labels.Add('auto-import') }

    if ($meta.ContainsKey('Epic')) {
        $epics = $meta['Epic'] -split '/' | ForEach-Object { $_.Trim() } | Where-Object { $_ }
        foreach ($e in $epics) {
            $slug = 'epic:' + (New-Slug $e)
            if (-not $labels.Contains($slug)) { $labels.Add($slug) }
        }
    }
    if ($meta.ContainsKey('Phase')) {
        $pl = 'phase:' + $meta['Phase']
        if (-not $labels.Contains($pl)) { $labels.Add($pl) }
    }

    $labelArg = ($labels -join ',')
    if ($DryRun) {
        Write-Host "[DryRun] Criaria issue: $title | Labels: $labelArg" -ForegroundColor Gray
        continue
    }

    Write-Host "Criando issue: $title" -ForegroundColor Green
    gh issue create --repo $Repo --title $title --body-file $f.FullName --label $labelArg | Out-Null
    $created++
}

Write-Host "Concluído. Criadas: $created | Skipped: $skipped | DryRun: $($DryRun.IsPresent)" -ForegroundColor Cyan
