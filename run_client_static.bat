@echo off
title Windows 11 Storage Monitor Client
color 0A
cls
echo ============================================================
echo   Windows 11 Storage Monitor Client
echo ============================================================
echo.

set SERVER_URL=%~1
if "%SERVER_URL%"=="" set /p SERVER_URL="Indirizzo del server (es. http://192.168.1.100:8080): "
if "%SERVER_URL%"=="" set SERVER_URL=http://localhost:8080

echo Server: %SERVER_URL%
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0win_client.ps1" -ServerUrl "%SERVER_URL%" -IntervalSeconds 10

pause
