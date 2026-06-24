# Starts the backend using the venv's Python directly.
# No venv activation or PATH setup needed — avoids the
# "uvicorn is not recognized" / greenlet-build issues on Windows.
#
# Usage (from anywhere):
#   powershell -ExecutionPolicy Bypass -File backend\run.ps1

$ErrorActionPreference = "Stop"
$venvPy = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $venvPy)) {
    Write-Host "No venv found. Creating one and installing dependencies..." -ForegroundColor Yellow
    python -m venv (Join-Path $PSScriptRoot ".venv")
    & $venvPy -m pip install --upgrade pip wheel
    & $venvPy -m pip install --only-binary=:all: greenlet
    & $venvPy -m pip install -r (Join-Path $PSScriptRoot "requirements.txt")
}

Write-Host "Starting API on http://localhost:8000 ..." -ForegroundColor Green
Set-Location $PSScriptRoot
& $venvPy -m uvicorn app.main:app --reload --port 8000
