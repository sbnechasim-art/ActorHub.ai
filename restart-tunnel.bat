@echo off
chcp 65001 >nul
title Restart Cloudflare Tunnel

echo.
echo  ╔═══════════════════════════════════════════════════════════╗
echo  ║           Restarting Cloudflare Tunnel                    ║
echo  ╚═══════════════════════════════════════════════════════════╝
echo.

cd /d "C:\ActorHub.ai 1.1"

:: Kill existing tunnels
echo [1/4] Stopping existing tunnels...
taskkill /F /IM cloudflared.exe >nul 2>&1
taskkill /F /IM ngrok.exe >nul 2>&1
timeout /t 1 /nobreak >nul
echo      Done.

:: Set cloudflared path
set CLOUDFLARED_PATH=cloudflared
if exist "C:\Program Files (x86)\cloudflared\cloudflared.exe" set CLOUDFLARED_PATH="C:\Program Files (x86)\cloudflared\cloudflared.exe"
if exist "C:\Program Files\cloudflared\cloudflared.exe" set CLOUDFLARED_PATH="C:\Program Files\cloudflared\cloudflared.exe"

:: Start cloudflared
echo [2/4] Starting Cloudflare Tunnel...
del "%TEMP%\cloudflared.log" 2>nul
start "Cloudflare Tunnel" /MIN cmd /c "%CLOUDFLARED_PATH% tunnel --url http://localhost:9000 2^>^&1 ^> "%TEMP%\cloudflared.log""

:: Wait and get URL
echo [3/4] Waiting for tunnel URL...
set TUNNEL_URL=
set RETRY_COUNT=0

:WAIT_LOOP
timeout /t 2 /nobreak >nul
set /a RETRY_COUNT+=1

for /f "delims=" %%u in ('powershell -Command "$content = Get-Content '%TEMP%\cloudflared.log' -ErrorAction SilentlyContinue; if ($content) { $match = [regex]::Match($content, 'https://[a-zA-Z0-9-]+\.trycloudflare\.com'); if ($match.Success) { $match.Value } }"') do set TUNNEL_URL=%%u

if "%TUNNEL_URL%"=="" (
    if %RETRY_COUNT% LSS 10 (
        echo      Waiting... (%RETRY_COUNT%/10)
        goto WAIT_LOOP
    )
)

if "%TUNNEL_URL%"=="" (
    echo.
    echo  ERROR: Could not get tunnel URL.
    echo  Check log: %TEMP%\cloudflared.log
    pause
    exit /b 1
)

echo      Found: %TUNNEL_URL%

:: Update .env
echo [4/4] Updating .env file...
powershell -Command "(Get-Content 'apps\api\.env') -replace 'S3_PUBLIC_URL=.*', 'S3_PUBLIC_URL=%TUNNEL_URL%' | Set-Content 'apps\api\.env'"
echo      Done.

echo.
echo  ╔═══════════════════════════════════════════════════════════╗
echo  ║              Tunnel Ready!                                ║
echo  ╠═══════════════════════════════════════════════════════════╣
echo  ║                                                           ║
echo  ║   URL: %TUNNEL_URL%
echo  ║                                                           ║
echo  ║   .env updated automatically!                             ║
echo  ║                                                           ║
echo  ║   NOTE: Restart API to apply changes:                     ║
echo  ║         restart-api.bat                                   ║
echo  ║                                                           ║
echo  ╚═══════════════════════════════════════════════════════════╝
echo.
pause
