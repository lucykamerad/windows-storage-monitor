@echo off
title Disinstallatore Client Windows Storage Monitor
color 0C
cls
echo ============================================================
echo   DISINSTALLATORE CLIENT WINDOWS STORAGE MONITOR
echo ============================================================
echo.

set TARGET_DIR=%LOCALAPPDATA%\WindowsStorageMonitor
set STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup

echo [1/3] Arresto del processo in corso...
taskkill /f /im StorageMonitorClient.exe 2>nul

echo [2/3] Rimozione dall'avvio automatico...
if exist "%STARTUP_DIR%\StorageMonitorClient.vbs" del "%STARTUP_DIR%\StorageMonitorClient.vbs"

echo [3/3] Eliminazione file di programma...
if exist "%TARGET_DIR%" rmdir /s /q "%TARGET_DIR%"

echo.
echo ============================================================
echo  🗑️ DISINSTALLAZIONE COMPLETATA CON SUCCESSO!
echo  Il client e stato rimosso dall'avvio automatico e dal PC.
echo ============================================================
echo.
pause
