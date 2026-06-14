# Run the Eldervale GM orchestrator locally (PowerShell).
# Usage:  ./scripts/run_local.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root

if (-not (Test-Path ".venv")) {
    Write-Host "Creating virtualenv..." -ForegroundColor Cyan
    python -m venv .venv
}
& ".venv\Scripts\python.exe" -m pip install --quiet --upgrade pip
& ".venv\Scripts\python.exe" -m pip install --quiet -r requirements.txt

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example (LLM_PROVIDER=mock by default)." -ForegroundColor Yellow
}

Write-Host "Starting GM on http://localhost:8000 ..." -ForegroundColor Green
& ".venv\Scripts\python.exe" -m uvicorn agents.game_master.app:app --reload --port 8000
