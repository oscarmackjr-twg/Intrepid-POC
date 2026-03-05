# dev.ps1 — PowerShell developer commands for intrepid-poc
# Usage: .\dev.ps1 <target>
# Targets: setup, migrate, run-backend, run-frontend

param(
    [Parameter(Position=0)]
    [ValidateSet("setup", "migrate", "run-backend", "run-frontend")]
    [string]$Target = "help"
)

$BackendDir = "$PSScriptRoot\backend"
$FrontendDir = "$PSScriptRoot\frontend"
$Venv = "$BackendDir\venv\Scripts"

function Invoke-Setup {
    Write-Host "Creating Python virtual environment..." -ForegroundColor Cyan
    python -m venv "$BackendDir\venv"

    Write-Host "Installing Python dependencies..." -ForegroundColor Cyan
    & "$Venv\pip" install `
        --trusted-host pypi.org `
        --trusted-host files.pythonhosted.org `
        -r "$BackendDir\requirements.txt"

    Write-Host "Installing frontend dependencies..." -ForegroundColor Cyan
    Push-Location $FrontendDir
    npm install
    Pop-Location

    Write-Host "Setup complete." -ForegroundColor Green
}

function Invoke-Migrate {
    Write-Host "Running Alembic migrations..." -ForegroundColor Cyan
    Push-Location $BackendDir
    & "$Venv\alembic" upgrade head
    Pop-Location
}

function Invoke-RunBackend {
    Write-Host "Starting backend at http://localhost:8000 ..." -ForegroundColor Cyan
    Push-Location $BackendDir
    & "$Venv\uvicorn" api.main:app --reload --host 0.0.0.0 --port 8000
    Pop-Location
}

function Invoke-RunFrontend {
    Write-Host "Starting frontend at http://localhost:5173 ..." -ForegroundColor Cyan
    Push-Location $FrontendDir
    npm run dev
    Pop-Location
}

switch ($Target) {
    "setup"        { Invoke-Setup }
    "migrate"      { Invoke-Migrate }
    "run-backend"  { Invoke-RunBackend }
    "run-frontend" { Invoke-RunFrontend }
    default {
        Write-Host ""
        Write-Host "Usage: .\dev.ps1 <target>" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "  setup         Create venv, install Python + npm dependencies"
        Write-Host "  migrate       Run Alembic database migrations"
        Write-Host "  run-backend   Start FastAPI at http://localhost:8000"
        Write-Host "  run-frontend  Start Vite dev server at http://localhost:5173"
        Write-Host ""
    }
}
