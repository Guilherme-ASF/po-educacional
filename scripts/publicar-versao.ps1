# Uso: .\scripts\publicar-versao.ps1 -Versao v0.2.0 -Push
# Restaura arquivos do _staging, aplica overlay (se existir), git add SOMENTE o manifest da versao.

param(
    [Parameter(Mandatory = $true)]
    [string]$Versao,

    [string]$Mensagem = "",

    [switch]$Push
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

$tag = if ($Versao -match "^v") { $Versao } else { "v$Versao" }
$manifestFile = Join-Path $PSScriptRoot "manifests\$tag.txt"
if (-not (Test-Path $manifestFile)) {
    throw "Manifest nao encontrado: $manifestFile"
}

$defaultMessages = @{
    "v0.1.0" = "chore: esqueleto FastAPI + React (Vite)"
    "v0.2.0" = "feat: parser de entrada e diagnostico automatico"
    "v0.3.0" = "feat: metodo grafico para PL com 2 variaveis"
    "v0.4.0" = "feat: Simplex pedagogico com tableau e fracoes"
    "v0.5.0" = "feat: dualidade forte/fraca e painel primal-dual"
    "v0.6.0" = "feat: relaxacao linear e Branch and Bound"
    "v0.7.0" = "feat: Branch and Cut e algoritmo genetico"
    "v0.8.0" = "docs: README, logo PPGCC e scripts de publicacao"
}
if (-not $Mensagem) {
    $Mensagem = $defaultMessages[$tag]
    if (-not $Mensagem) { $Mensagem = "release: $tag" }
}

$Staging = Join-Path $Root "_staging"
if (-not (Test-Path $Staging)) {
    throw "Pasta _staging/ nao existe. Rode antes: .\scripts\sync-staging.ps1"
}

$paths = Get-Content $manifestFile | ForEach-Object { $_.Trim() } |
    Where-Object { $_ -and -not $_.StartsWith("#") }

foreach ($rel in $paths) {
    $from = Join-Path $Staging $rel
    $to = Join-Path $Root $rel
    if (Test-Path $from) {
        New-Item -ItemType Directory -Force -Path (Split-Path $to -Parent) | Out-Null
        Copy-Item -Path $from -Destination $to -Force
    }
}

$overlay = Join-Path $PSScriptRoot "overlays\$tag"
if (Test-Path $overlay) {
    Get-ChildItem -Path $overlay -Recurse -File | ForEach-Object {
        $rel = $_.FullName.Substring($overlay.Length + 1)
        $dest = Join-Path $Root $rel
        New-Item -ItemType Directory -Force -Path (Split-Path $dest -Parent) | Out-Null
        Copy-Item -Path $_.FullName -Destination $dest -Force
    }
}

if (-not (Test-Path (Join-Path $Root ".git"))) {
    git init
    git branch -M main
}

foreach ($rel in $paths) {
    if (Test-Path (Join-Path $Root $rel)) {
        git add -- "$rel"
    } else {
        Write-Warning "Arquivo nao encontrado (ignorado no add): $rel"
    }
}

git commit -m $Mensagem

# Tag leve (sem GPG) — evita erro "unable to sign the tag" no Windows
if (git tag -l $tag) {
    $prevEA = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    git tag -d $tag 2>&1 | Out-Null
    $ErrorActionPreference = $prevEA
}
git -c tag.gpgSign=false tag -f $tag

Write-Host "Commit e tag $tag criados."
Write-Host "Arquivos incluidos nesta versao:"
$paths | ForEach-Object { Write-Host "  $_" }

if ($Push) {
    $remote = git remote
    if (-not $remote) {
        Write-Host ""
        Write-Host "AVISO: remoto nao configurado. Execute antes do -Push:"
        Write-Host '  git remote add origin https://github.com/Guilherme-ASF/po-educacional.git'
        exit 1
    }
    git push -u origin main
    git push origin $tag
    Write-Host "Enviado para origin (main + $tag)."
} else {
    Write-Host ""
    Write-Host "Para enviar ao GitHub:"
    Write-Host "  git push -u origin main"
    Write-Host "  git push origin $tag"
}

$restaurar = Join-Path $PSScriptRoot "restaurar-desenvolvimento.ps1"
if (Test-Path (Join-Path $Root "_dev_snapshot")) {
    Write-Host ""
    Write-Host "Restaurando projeto completo local (nao vai para o GitHub)..."
    & $restaurar
}
