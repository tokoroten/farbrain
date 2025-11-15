#!/usr/bin/env pwsh
# GitHub Secrets Setup Script for Render Deployment

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "GitHub Secrets Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if gh CLI is installed
if (!(Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: GitHub CLI (gh) is not installed" -ForegroundColor Red
    Write-Host "Please install from: https://cli.github.com/" -ForegroundColor Yellow
    exit 1
}

# Check if authenticated
$authStatus = gh auth status 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Not authenticated with GitHub CLI" -ForegroundColor Red
    Write-Host "Please run: gh auth login" -ForegroundColor Yellow
    exit 1
}

Write-Host "GitHub CLI is ready!" -ForegroundColor Green
Write-Host ""

# Set OPENAI_API_KEY
Write-Host "Setting up OPENAI_API_KEY..." -ForegroundColor Yellow
Write-Host "Enter your OpenAI API key (starts with sk-): " -NoNewline
$openaiKey = Read-Host
if ($openaiKey -match "^sk-") {
    gh secret set OPENAI_API_KEY --body $openaiKey
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ OPENAI_API_KEY set successfully" -ForegroundColor Green
    } else {
        Write-Host "✗ Failed to set OPENAI_API_KEY" -ForegroundColor Red
    }
} else {
    Write-Host "✗ Invalid API key format (should start with sk-)" -ForegroundColor Red
}
Write-Host ""

# Set ADMIN_PASSWORD
Write-Host "Setting up ADMIN_PASSWORD..." -ForegroundColor Yellow
Write-Host "Enter admin password for session management: " -NoNewline
$adminPassword = Read-Host
if ($adminPassword.Length -ge 8) {
    gh secret set ADMIN_PASSWORD --body $adminPassword
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ ADMIN_PASSWORD set successfully" -ForegroundColor Green
    } else {
        Write-Host "✗ Failed to set ADMIN_PASSWORD" -ForegroundColor Red
    }
} else {
    Write-Host "✗ Password too short (minimum 8 characters)" -ForegroundColor Red
}
Write-Host ""

# List all secrets
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Current GitHub Secrets:" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
gh secret list

Write-Host ""
Write-Host "Setup complete!" -ForegroundColor Green
Write-Host "You can now deploy to Render.com" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Go to https://dashboard.render.com/" -ForegroundColor White
Write-Host "2. Create a new Blueprint" -ForegroundColor White
Write-Host "3. Connect your GitHub repository" -ForegroundColor White
Write-Host "4. Render will use render.yaml for configuration" -ForegroundColor White
Write-Host ""
