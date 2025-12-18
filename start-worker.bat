@echo off
echo Starting ActorHub.ai Celery Worker...
cd /d "%~dp0apps\worker"
call ..\api\venv\Scripts\activate.bat
celery -A celery_app worker --loglevel=info --pool=solo
