@echo off
title ActorHub.ai Development Server
echo ========================================
echo   ActorHub.ai Platform Launcher
echo ========================================
echo.

:: Check prerequisites
echo [1/5] Checking prerequisites...
where python >nul 2>&1 || (echo ERROR: Python not found & pause & exit /b 1)
where node >nul 2>&1 || (echo ERROR: Node.js not found & pause & exit /b 1)

:: Run migrations
echo [2/5] Running database migrations...
cd /d "C:\ActorHub.ai 1.1\apps\api"
call alembic upgrade head
if errorlevel 1 (echo WARNING: Migration failed, continuing anyway...)

:: Start API in new window
echo [3/5] Starting API server...
start "ActorHub API" cmd /k "cd /d C:\ActorHub.ai 1.1\apps\api && uvicorn app.main:app --reload --port 8000"

:: Wait for API to start
timeout /t 3 /nobreak >nul

:: Start Worker in new window
echo [4/5] Starting Celery worker...
start "ActorHub Worker" cmd /k "cd /d C:\ActorHub.ai 1.1\apps\worker && celery -A celery_app worker -Q payouts,default -l info"

:: Start Frontend in new window
echo [5/5] Starting Frontend...
start "ActorHub Frontend" cmd /k "cd /d C:\ActorHub.ai 1.1\apps\web && npm run dev"

echo.
echo ========================================
echo   All services started!
echo ========================================
echo.
echo   API:      http://localhost:8000
echo   Docs:     http://localhost:8000/docs
echo   Frontend: http://localhost:3000
echo.
echo   Press any key to open the app...
pause >nul
start http://localhost:3000
