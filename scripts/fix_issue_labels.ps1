Param(
    [Parameter(Mandatory=$true)][string]$Repo,
    [switch]$DryRun
)

$basePath = Join-Path $PSScriptRoot '..' | Join-Path -ChildPath 'issues'

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

Write-Host "Buscando issues existentes..." -ForegroundColor Cyan
$issues = gh issue list --repo $Repo --state all --limit 100 --json number,title | ConvertFrom-Json

$files = Get-ChildItem -Path $basePath -File -Filter 'GH-*.md' | Sort-Object Name
$updated = 0

foreach ($f in $files) {
    $raw = Get-Content $f.FullName -Raw
    $meta = Get-Meta -Raw $raw
    $content = $raw -replace '(?s)<!--.*?-->', ''
    $titleLine = ($content -split "`n" | Where-Object { $_ -match '^# \S' } | Select-Object -First 1)
    if (-not $titleLine) { continue }
    $title = $titleLine.Substring(2).Trim()

    $issue = $issues | Where-Object { $_.title -eq $title } | Select-Object -First 1
    if (-not $issue) {
        Write-Host "Issue não encontrada: $title" -ForegroundColor Yellow
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
        Write-Host "[DryRun] Issue #$($issue.number): $title | Labels: $labelArg" -ForegroundColor Gray
    } else {
        Write-Host "Atualizando issue #$($issue.number): $title" -ForegroundColor Green
        gh issue edit $issue.number --repo $Repo --add-label $labelArg | Out-Null
        $updated++
    }
}

Write-Host "Concluído. Atualizadas: $updated | DryRun: $($DryRun.IsPresent)" -ForegroundColor Cyan
