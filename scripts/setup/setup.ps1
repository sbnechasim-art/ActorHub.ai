# ActorHub.ai - Local Development Setup Script (Windows PowerShell)
# Run this script to set up the development environment

$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  ActorHub.ai Local Development Setup" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# Check prerequisites
Write-Host "`nChecking prerequisites..." -ForegroundColor Yellow

$docker = Get-Command docker -ErrorAction SilentlyContinue
if (-not $docker) {
    Write-Host "Docker is required but not installed." -ForegroundColor Red
    exit 1
}

$node = Get-Command node -ErrorAction SilentlyContinue
if (-not $node) {
    Write-Host "Node.js is required but not installed." -ForegroundColor Red
    exit 1
}

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Host "Python is required but not installed." -ForegroundColor Red
    exit 1
}

Write-Host "All prerequisites satisfied!" -ForegroundColor Green

# Start Docker services
Write-Host "`nStarting Docker services..." -ForegroundColor Yellow
docker-compose up -d

# Wait for services
Write-Host "`nWaiting for services to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# Setup Python backend
Write-Host "`nSetting up Python backend..." -ForegroundColor Yellow
Set-Location apps/api

# Create virtual environment if it doesn't exist
if (-not (Test-Path "venv")) {
    python -m venv venv
}

# Activate virtual environment
& .\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Run database migrations
Write-Host "`nRunning database migrations..." -ForegroundColor Yellow
alembic upgrade head

Set-Location ../..

# Setup Node.js frontend
Write-Host "`nSetting up Node.js frontend..." -ForegroundColor Yellow
Set-Location apps/web
npm install
Set-Location ../..

Write-Host "`n==========================================" -ForegroundColor Green
Write-Host "  Setup Complete!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""
Write-Host "To start the development servers:"
Write-Host ""
Write-Host "  Backend API:" -ForegroundColor Cyan
Write-Host "    cd apps/api; .\venv\Scripts\Activate.ps1"
Write-Host "    uvicorn app.main:app --reload --port 8000"
Write-Host ""
Write-Host "  Frontend:" -ForegroundColor Cyan
Write-Host "    cd apps/web; npm run dev"
Write-Host ""
Write-Host "Access points:"
Write-Host "  - Frontend: http://localhost:3000"
Write-Host "  - API: http://localhost:8000"
Write-Host "  - API Docs: http://localhost:8000/docs"
Write-Host "  - MinIO Console: http://localhost:9001"
Write-Host "  - Qdrant Dashboard: http://localhost:6333/dashboard"
