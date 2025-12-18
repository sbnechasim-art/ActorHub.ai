@echo off
echo Stopping ActorHub.ai Docker Services...
cd /d "%~dp0"
docker-compose down
echo.
echo Docker services stopped.
echo Note: API, Web, and Worker need to be stopped manually (Ctrl+C in their terminals)
pause
