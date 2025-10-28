@echo off
echo ========================================
echo FarBrain Startup Script
echo ========================================
echo.
echo Starting 3 services:
echo 1. Backend (FastAPI)
echo 2. Frontend (Vite)
echo 3. Cloudflare Tunnel
echo.
echo Each service will open in a new window.
echo Press Ctrl+C in each window to stop.
echo ========================================
echo.

REM Create frontend .env file if it doesn't exist
if not exist "frontend\.env" (
    echo Creating frontend\.env file...
    (
        echo VITE_API_URL=https://api-farbrain.easyrec.app
        echo VITE_WS_URL=wss://api-farbrain.easyrec.app
    ) > "frontend\.env"
    echo ✓ Created frontend\.env
) else (
    echo ✓ frontend\.env already exists
)
echo.

REM Start Backend
echo Starting Backend...
start "FarBrain Backend" cmd /k "cd /d %~dp0backend && uv run uvicorn app.main:app --host 0.0.0.0 --port 8000"
timeout /t 2 /nobreak >nul

REM Start Frontend
echo Starting Frontend...
start "FarBrain Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"
timeout /t 2 /nobreak >nul

REM Start Cloudflare Tunnel
echo Starting Cloudflare Tunnel...
start "FarBrain Tunnel" cmd /k "cd /d %~dp0 && cloudflared tunnel --config cloudflare-tunnel-config.yml run farbrain"
timeout /t 2 /nobreak >nul

echo.
echo ========================================
echo All services started!
echo ========================================
echo.
echo Access URLs:
echo - Local Frontend: http://localhost:5173
echo - Local Backend:  http://localhost:8000
echo - Public URL:     https://farbrain.easyrec.app
echo - API Docs:       https://api-farbrain.easyrec.app/docs
echo.
echo To stop all services, close all 3 windows.
echo ========================================
pause
