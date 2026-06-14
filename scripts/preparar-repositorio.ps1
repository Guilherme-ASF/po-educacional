# Uso (uma vez): .\scripts\preparar-repositorio.ps1
# Copia o código completo para _staging, aplica overlay v0.1.0 e prepara o primeiro commit.

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

$Staging = Join-Path $Root "_staging"
if (Test-Path $Staging) {
    Remove-Item -Recurse -Force $Staging
}
New-Item -ItemType Directory -Path $Staging | Out-Null

$pathsToBackup = @(
    "backend/app",
    "backend/requirements.txt",
    "frontend/src",
    "frontend/package.json",
    "frontend/package-lock.json",
    "frontend/vite.config.ts",
    "frontend/index.html",
    "frontend/tsconfig.json",
    "README.md"
)

foreach ($rel in $pathsToBackup) {
    $src = Join-Path $Root $rel
    if (-not (Test-Path $src)) { continue }
    $dst = Join-Path $Staging $rel
    New-Item -ItemType Directory -Force -Path (Split-Path $dst -Parent) | Out-Null
    Copy-Item -Path $src -Destination $dst -Recurse -Force
}

$overlay = Join-Path $PSScriptRoot "overlays\v0.1.0"
if (Test-Path $overlay) {
    Copy-Item -Path (Join-Path $overlay "*") -Destination $Root -Recurse -Force
}

Write-Host "Backup completo em _staging/"
Write-Host "Overlay v0.1.0 aplicado na pasta de trabalho."
Write-Host ""
Write-Host "Proximo passo:"
Write-Host "  git init"
Write-Host "  .\scripts\publicar-versao.ps1 -Versao v0.1.0 -Push"
