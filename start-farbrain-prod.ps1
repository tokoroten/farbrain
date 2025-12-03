#!/usr/bin/env pwsh
# FarBrain Production Startup Script (PowerShell)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "FarBrain Production Startup Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Starting 3 services:" -ForegroundColor Yellow
Write-Host "1. Backend (FastAPI)" -ForegroundColor White
Write-Host "2. Frontend (Production Build)" -ForegroundColor White
Write-Host "3. Cloudflare Tunnel" -ForegroundColor White
Write-Host ""
Write-Host "Each service will open in a new window." -ForegroundColor Gray
Write-Host "Press Ctrl+C in each window to stop." -ForegroundColor Gray
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Get script directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Create frontend .env file for production hosting
Write-Host "Setting up production environment..." -ForegroundColor Yellow
$envFile = Join-Path $scriptDir "frontend\.env"
@"
VITE_API_URL=https://api-farbrain.easyrec.app
VITE_WS_URL=wss://api-farbrain.easyrec.app
"@ | Out-File -FilePath $envFile -Encoding utf8 -Force
Write-Host "Created frontend\.env for production hosting" -ForegroundColor Green
Write-Host ""

# Build Frontend
Write-Host "Building Frontend (this may take a moment)..." -ForegroundColor Yellow
$frontendDir = Join-Path $scriptDir "frontend"
Push-Location $frontendDir
try {
    npm run build
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Frontend build failed!" -ForegroundColor Red
        Pop-Location
        exit 1
    }
    Write-Host "Frontend build completed!" -ForegroundColor Green
}
finally {
    Pop-Location
}
Write-Host ""

# Start Backend (without --reload for production)
Write-Host "Starting Backend..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$scriptDir\backend'; uv run uvicorn app.main:app --host 0.0.0.0 --port 8000" -WindowStyle Normal
Start-Sleep -Seconds 2

# Start Frontend (serve static files)
Write-Host "Starting Frontend (static file server)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$scriptDir\frontend'; npx serve dist -l 5173" -WindowStyle Normal
Start-Sleep -Seconds 2

# Start Cloudflare Tunnel
Write-Host "Starting Cloudflare Tunnel..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$scriptDir'; cloudflared tunnel --config cloudflare-tunnel-config.yml run farbrain" -WindowStyle Normal
Start-Sleep -Seconds 2

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "All services started!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Access URLs:" -ForegroundColor Yellow
Write-Host "  - Local Frontend: " -NoNewline -ForegroundColor White
Write-Host "http://localhost:5173" -ForegroundColor Blue
Write-Host "  - Local Backend:  " -NoNewline -ForegroundColor White
Write-Host "http://localhost:8000" -ForegroundColor Blue
Write-Host "  - Public URL:     " -NoNewline -ForegroundColor White
Write-Host "https://farbrain.easyrec.app" -ForegroundColor Green
Write-Host "  - API Docs:       " -NoNewline -ForegroundColor White
Write-Host "https://api-farbrain.easyrec.app/docs" -ForegroundColor Green
Write-Host ""
Write-Host "Mode: " -NoNewline -ForegroundColor White
Write-Host "PRODUCTION (Optimized Build)" -ForegroundColor Green
Write-Host "Frontend will connect to: " -NoNewline -ForegroundColor White
Write-Host "https://api-farbrain.easyrec.app" -ForegroundColor Blue
Write-Host ""
Write-Host "To stop all services, close all 3 windows." -ForegroundColor Gray
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press any key to exit this window..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
