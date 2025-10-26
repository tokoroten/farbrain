@echo off
REM FarBrain Development Environment Startup Script
REM This script starts both backend and frontend servers in clean state

echo ============================================
echo FarBrain Development Environment
echo ============================================
echo.

REM Kill all existing Python processes (backend servers)
echo [1/4] Stopping all existing backend processes...
taskkill /F /IM python.exe >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo     Backend processes stopped
) else (
    echo     No backend processes running
)
timeout /t 1 /nobreak >nul
echo.

REM Start backend server
echo [2/4] Starting backend server on port 8000...
cd backend
start "FarBrain Backend" cmd /k "uv run uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000"
cd ..
echo     Backend starting... (wait 10 seconds)
timeout /t 10 /nobreak >nul
echo.

REM Start frontend server
echo [3/4] Starting frontend server on port 5173...
cd frontend
start "FarBrain Frontend" cmd /k "npm run dev"
cd ..
echo     Frontend starting... (wait 5 seconds)
timeout /t 5 /nobreak >nul
echo.

REM Open browser
echo [4/4] Opening browser...
start http://localhost:5173
echo.

echo ============================================
echo Development servers started successfully!
echo ============================================
echo.
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:5173
echo.
echo Admin Password: admin123
echo.
echo Press any key to exit this window...
echo (Backend and Frontend will continue running in separate windows)
pause >nul
