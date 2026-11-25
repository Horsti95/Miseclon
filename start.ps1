$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    Write-Host "[Miseclon] Erstelle Python-Umgebung in .venv ..." -ForegroundColor Cyan
    python -m venv .venv
    .\.venv\Scripts\pip.exe install -r requirements.txt
}

if (-not (Test-Path ".\frontend\dist\index.html")) {
    Write-Host "[Miseclon] Baue Web-Frontend ..." -ForegroundColor Cyan
    Push-Location frontend
    npm install
    npm run build
    Pop-Location
}

.\.venv\Scripts\python.exe -m backend.run_local
