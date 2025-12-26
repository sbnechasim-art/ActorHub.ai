@echo off
chcp 65001 >nul
title Restart ActorHub API

echo Restarting API server...

:: Kill existing API
taskkill /F /FI "WINDOWTITLE eq ActorHub API*" >nul 2>&1
timeout /t 2 /nobreak >nul

:: Start new API
cd /d "C:\ActorHub.ai 1.1\apps\api"
start "ActorHub API" cmd /k "call .venv\Scripts\activate && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

echo API restarted on http://localhost:8000
timeout /t 2 /nobreak >nul
