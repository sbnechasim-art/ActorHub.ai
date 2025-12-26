@echo off
chcp 65001 >nul
title ActorHub.ai Platform Launcher

echo.
echo  ╔═══════════════════════════════════════════════════════════╗
echo  ║           ActorHub.ai Platform Launcher                   ║
echo  ║                                                           ║
echo  ║   Starting all services...                                ║
echo  ╚═══════════════════════════════════════════════════════════╝
echo.

cd /d "C:\ActorHub.ai 1.1"

:: ============================================
:: Step 1: Start Docker containers
:: ============================================
echo [1/5] Starting Docker containers (PostgreSQL, Redis, MinIO, Qdrant)...
docker-compose up -d
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to start Docker containers!
    echo Make sure Docker Desktop is running.
    pause
    exit /b 1
)
echo      Docker containers started successfully!
echo.

:: Wait for services to be ready
echo      Waiting for services to initialize...
timeout /t 5 /nobreak >nul

:: ============================================
:: Step 2: Start Cloudflare Tunnel for MinIO
:: ============================================
echo [2/5] Starting Cloudflare Tunnel for MinIO...

:: Kill existing cloudflared/ngrok if running
taskkill /F /IM cloudflared.exe >nul 2>&1
taskkill /F /IM ngrok.exe >nul 2>&1

:: Set cloudflared path (check both possible locations)
set CLOUDFLARED_PATH=cloudflared
if exist "C:\Program Files (x86)\cloudflared\cloudflared.exe" set CLOUDFLARED_PATH="C:\Program Files (x86)\cloudflared\cloudflared.exe"
if exist "C:\Program Files\cloudflared\cloudflared.exe" set CLOUDFLARED_PATH="C:\Program Files\cloudflared\cloudflared.exe"

:: Start cloudflared tunnel in background and capture output
del "%TEMP%\cloudflared.log" 2>nul
start "Cloudflare Tunnel" /MIN cmd /c "%CLOUDFLARED_PATH% tunnel --url http://localhost:9000 2^>^&1 ^> "%TEMP%\cloudflared.log""

:: Wait for tunnel to start and get URL
echo      Waiting for tunnel to initialize...
set TUNNEL_URL=
set RETRY_COUNT=0

:WAIT_FOR_TUNNEL
timeout /t 2 /nobreak >nul
set /a RETRY_COUNT+=1

:: Try to get URL using PowerShell (more reliable)
for /f "delims=" %%u in ('powershell -Command "$content = Get-Content '%TEMP%\cloudflared.log' -ErrorAction SilentlyContinue; if ($content) { $match = [regex]::Match($content, 'https://[a-zA-Z0-9-]+\.trycloudflare\.com'); if ($match.Success) { $match.Value } }"') do set TUNNEL_URL=%%u

if "%TUNNEL_URL%"=="" (
    if %RETRY_COUNT% LSS 10 (
        echo      Waiting... (%RETRY_COUNT%/10)
        goto WAIT_FOR_TUNNEL
    )
)

if "%TUNNEL_URL%"=="" (
    echo      ERROR: Could not get tunnel URL after 20 seconds.
    echo      Check log: %TEMP%\cloudflared.log
    echo      You may need to update S3_PUBLIC_URL manually.
) else (
    echo      Cloudflare Tunnel: %TUNNEL_URL%
    echo      (No interstitial page - Replicate can access directly!)

    :: Update .env file with new tunnel URL
    powershell -Command "(Get-Content 'apps\api\.env') -replace 'S3_PUBLIC_URL=.*', 'S3_PUBLIC_URL=%TUNNEL_URL%' | Set-Content 'apps\api\.env'"
    echo      Updated S3_PUBLIC_URL in .env
)
echo.

:: ============================================
:: Step 3: Start Celery Worker
:: ============================================
echo [3/5] Starting Celery worker...
cd apps\worker
start "Celery Worker" cmd /k "call ..\api\.venv\Scripts\activate && celery -A celery_app worker --loglevel=info --pool=solo -Q training,face,notifications,cleanup,payouts"
cd ..\..
echo      Celery worker started!
echo.

:: ============================================
:: Step 4: Start API Server
:: ============================================
echo [4/5] Starting API server...
cd apps\api
start "ActorHub API" cmd /k "call .venv\Scripts\activate && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
cd ..\..
echo      API server started on http://localhost:8000
echo.

:: ============================================
:: Step 5: Start Web Frontend
:: ============================================
echo [5/5] Starting Web frontend...
cd apps\web
start "ActorHub Web" cmd /k "npm run dev"
cd ..\..
echo      Web frontend started on http://localhost:3000
echo.

:: ============================================
:: Done!
:: ============================================
echo.
echo  ╔═══════════════════════════════════════════════════════════╗
echo  ║                    Platform Ready!                        ║
echo  ╠═══════════════════════════════════════════════════════════╣
echo  ║                                                           ║
echo  ║   Web App:     http://localhost:3000                      ║
echo  ║   API:         http://localhost:8000                      ║
echo  ║   API Docs:    http://localhost:8000/docs                 ║
echo  ║   MinIO:       http://localhost:9001                      ║
echo  ║   Tunnel Log:  %%TEMP%%\cloudflared.log                    ║
echo  ║                                                           ║
echo  ╚═══════════════════════════════════════════════════════════╝
echo.
echo  Press any key to open the web app in your browser...
pause >nul

start http://localhost:3000

echo.
echo  To stop all services, run: stop-platform.bat
echo.
