@echo off
REM Starts the backend using the venv's Python directly (cmd.exe).
REM No activation/PATH needed. Run from anywhere:  backend\run.bat
setlocal
set "HERE=%~dp0"
set "VENVPY=%HERE%.venv\Scripts\python.exe"

if not exist "%VENVPY%" (
    echo No venv found. Creating one and installing dependencies...
    python -m venv "%HERE%.venv"
    "%VENVPY%" -m pip install --upgrade pip wheel
    "%VENVPY%" -m pip install --only-binary=:all: greenlet
    "%VENVPY%" -m pip install -r "%HERE%requirements.txt"
)

echo Starting API on http://localhost:8000 ...
cd /d "%HERE%"
"%VENVPY%" -m uvicorn app.main:app --reload --port 8000
