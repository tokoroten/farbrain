#!/usr/bin/env pwsh
# FarBrain Local Development Startup Script

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "FarBrain Local Development Mode" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Get script directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Create frontend .env file for local development
Write-Host "Setting up local environment..." -ForegroundColor Yellow
$envFile = Join-Path $scriptDir "frontend\.env"
@"
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
"@ | Out-File -FilePath $envFile -Encoding utf8 -Force
Write-Host "✓ Created frontend\.env for local development" -ForegroundColor Green
Write-Host ""

Write-Host "Starting 2 services:" -ForegroundColor Yellow
Write-Host "1. Backend (FastAPI)" -ForegroundColor White
Write-Host "2. Frontend (Vite)" -ForegroundColor White
Write-Host ""
Write-Host "Each service will open in a new window." -ForegroundColor Gray
Write-Host "Press Ctrl+C in each window to stop." -ForegroundColor Gray
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Start Backend
Write-Host "Starting Backend..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$scriptDir\backend'; uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload" -WindowStyle Normal
Start-Sleep -Seconds 2

# Start Frontend
Write-Host "Starting Frontend..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$scriptDir\frontend'; npm run dev" -WindowStyle Normal
Start-Sleep -Seconds 2

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Local development services started!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Access URLs:" -ForegroundColor Yellow
Write-Host "  - Frontend: " -NoNewline -ForegroundColor White
Write-Host "http://localhost:5173" -ForegroundColor Blue
Write-Host "  - Backend:  " -NoNewline -ForegroundColor White
Write-Host "http://localhost:8000" -ForegroundColor Blue
Write-Host "  - API Docs: " -NoNewline -ForegroundColor White
Write-Host "http://localhost:8000/docs" -ForegroundColor Blue
Write-Host ""
Write-Host "Mode: " -NoNewline -ForegroundColor White
Write-Host "LOCAL DEVELOPMENT" -ForegroundColor Green
Write-Host "Frontend will connect to: " -NoNewline -ForegroundColor White
Write-Host "http://localhost:8000" -ForegroundColor Blue
Write-Host ""
Write-Host "To stop services, close both windows." -ForegroundColor Gray
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press any key to exit this window..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
