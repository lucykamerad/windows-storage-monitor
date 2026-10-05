@echo off
title Configura Avvio Automatico Windows 11
color 0B
cls
echo ============================================================
echo   Configurazione Avvio Automatico Client Windows 11
echo ============================================================
echo.

set STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
set CONFIG_DIR=%LOCALAPPDATA%\WindowsStorageMonitor

set /p SERVER_URL="Indirizzo del server (es. http://192.168.1.100:8080): "
if "%SERVER_URL%"=="" set SERVER_URL=http://localhost:8080
if not exist "%CONFIG_DIR%" mkdir "%CONFIG_DIR%"
>"%CONFIG_DIR%\server_url.txt" echo %SERVER_URL%

if exist StorageMonitorClient_Static.exe (
    copy /Y StorageMonitorClient_Static.exe "%STARTUP_DIR%\StorageMonitorClient_Static.exe"
    echo ✅ Eseguibile 'StorageMonitorClient_Static.exe' aggiunto all'avvio automatico di Windows!
) else (
    echo [!] 'StorageMonitorClient_Static.exe' non presente nella cartella attuale.
    echo Compilazione in corso prima di aggiungere all'avvio...
    call build_static_exe.bat
    if exist StorageMonitorClient_Static.exe (
        copy /Y StorageMonitorClient_Static.exe "%STARTUP_DIR%\StorageMonitorClient_Static.exe"
        echo ✅ Eseguibile 'StorageMonitorClient_Static.exe' aggiunto all'avvio automatico di Windows!
    ) else (
        echo [!] Impossibile trovare l'eseguibile. Creazione scorciatoia per lo script batch...
        copy /Y run_client_static.bat "%STARTUP_DIR%\run_client_static.bat"
        echo [!] Attenzione: run_client_static.bat chiedera' l'indirizzo del server a ogni avvio.
        echo ✅ Script 'run_client_static.bat' aggiunto all'avvio automatico di Windows!
    )
)

echo.
echo ============================================================
echo  CONFIGURAZIONE COMPLETATA!
echo  Ad ogni avvio di Windows 11, il monitoraggio dello storage
echo  verrà avviato automaticamente in background.
echo ============================================================
echo.
pause
