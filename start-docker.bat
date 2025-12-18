@echo off
echo Starting ActorHub.ai Docker Services...
cd /d "%~dp0"
docker-compose up -d
echo.
echo Waiting for services to be ready...
timeout /t 5 /nobreak >nul
docker ps --format "table {{.Names}}\t{{.Status}}"
echo.
echo Docker services started!
echo.
echo Now open 3 more terminals and run:
echo   Terminal 1: start-api.bat
echo   Terminal 2: start-web.bat
echo   Terminal 3: start-worker.bat
echo.
pause
