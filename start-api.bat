@echo off
echo Starting ActorHub.ai API Server...
cd /d "%~dp0apps\api"
call venv\Scripts\activate.bat
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
