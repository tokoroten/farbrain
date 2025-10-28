#!/usr/bin/env pwsh
# FarBrain Stop Script (PowerShell)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "FarBrain Stop Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Stop processes by name
$processesToStop = @(
    @{Name = "uvicorn"; Description = "Backend (FastAPI)"},
    @{Name = "node"; Description = "Frontend (Vite)"},
    @{Name = "cloudflared"; Description = "Cloudflare Tunnel"}
)

foreach ($proc in $processesToStop) {
    $processes = Get-Process -Name $proc.Name -ErrorAction SilentlyContinue
    if ($processes) {
        Write-Host "Stopping $($proc.Description)..." -ForegroundColor Yellow
        $processes | Stop-Process -Force
        Write-Host "✓ Stopped $($proc.Description)" -ForegroundColor Green
    } else {
        Write-Host "- $($proc.Description) not running" -ForegroundColor Gray
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "All services stopped!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press any key to exit..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
