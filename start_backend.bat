@echo off
REM Start backend server (Windows)

echo Starting FarBrain backend...

cd backend

REM Check if .env exists
if not exist .env (
    echo Error: .env file not found!
    echo Please copy .env.example to .env and configure it
    exit /b 1
)

REM Check if uv is installed
where uv >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Error: uv is not installed!
    echo Please install uv: https://github.com/astral-sh/uv
    exit /b 1
)

REM Install dependencies if needed
if not exist .venv (
    echo Installing dependencies...
    uv sync
)

REM Start the server
echo Starting FastAPI server on http://localhost:8001
uv run uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8001
