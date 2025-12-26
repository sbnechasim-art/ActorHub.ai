@echo off
chcp 65001 >nul
title ActorHub.ai Platform Shutdown

echo.
echo  ╔═══════════════════════════════════════════════════════════╗
echo  ║           ActorHub.ai Platform Shutdown                   ║
echo  ╚═══════════════════════════════════════════════════════════╝
echo.

cd /d "C:\ActorHub.ai 1.1"

echo [1/4] Stopping Cloudflare Tunnel...
taskkill /F /IM cloudflared.exe >nul 2>&1
taskkill /F /IM ngrok.exe >nul 2>&1
echo      Done.

echo [2/4] Stopping Celery worker...
taskkill /F /FI "WINDOWTITLE eq Celery Worker*" >nul 2>&1
taskkill /F /IM celery.exe >nul 2>&1
echo      Done.

echo [3/4] Stopping API server...
taskkill /F /FI "WINDOWTITLE eq ActorHub API*" >nul 2>&1
echo      Done.

echo [4/4] Stopping Web frontend...
taskkill /F /FI "WINDOWTITLE eq ActorHub Web*" >nul 2>&1
echo      Done.

echo.
set /p STOP_DOCKER="Stop Docker containers too? (y/n): "
if /i "%STOP_DOCKER%"=="y" (
    echo Stopping Docker containers...
    docker-compose down
    echo      Docker containers stopped.
)

echo.
echo  ╔═══════════════════════════════════════════════════════════╗
echo  ║              All services stopped!                        ║
echo  ╚═══════════════════════════════════════════════════════════╝
echo.
pause
