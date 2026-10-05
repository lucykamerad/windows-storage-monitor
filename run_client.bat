@echo off
title Windows 11 Storage Monitor Client
color 0A
cls
echo ============================================================
echo   Windows 11 Storage Monitor Client Launcher
echo ============================================================
echo.

set /p SERVER_IP="Inserisci l'IP del Server (es. 192.168.1.100 o lascia vuoto per localhost): "

if "%SERVER_IP%"=="" (
    set SERVER_URL=http://localhost:8080
) else (
    set SERVER_URL=http://%SERVER_IP%:8080
)

echo.
echo Avvio del monitoraggio storage in corso verso: %SERVER_URL%...
echo (Premi CTRL+C nella finestra della console per interrompere)
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0win_client.ps1" -ServerUrl "%SERVER_URL%" -IntervalSeconds 10

pause
