@echo off
title Installatore Rapido - Windows Storage Monitor
color 0A
cls
echo ============================================================
echo   INSTALLATORE RAPIDO - Windows Storage Monitor
echo ============================================================
echo.

set TARGET_DIR=%LOCALAPPDATA%\WindowsStorageMonitor
set STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
set EXE_NAME=StorageMonitorClient.exe

echo [1/3] Creazione cartella di installazione...
if not exist "%TARGET_DIR%" mkdir "%TARGET_DIR%"

set /p SERVER_URL="Indirizzo del server (es. http://192.168.1.100:8080): "
if "%SERVER_URL%"=="" set SERVER_URL=http://localhost:8080
>"%TARGET_DIR%\server_url.txt" echo %SERVER_URL%

echo [2/3] Copia dell'eseguibile...
copy /y "%~dp0%EXE_NAME%" "%TARGET_DIR%\%EXE_NAME%"

if not exist "%TARGET_DIR%\%EXE_NAME%" (
    echo [!] Errore: File %EXE_NAME% non trovato nella stessa cartella di questo bat.
    echo     Assicurati che %EXE_NAME% sia nella stessa cartella!
    pause
    exit /b 1
)

echo [3/3] Configurazione avvio automatico e avvio immediato...
echo Set WshShell = CreateObject("WScript.Shell") > "%STARTUP_DIR%\StorageMonitorClient.vbs"
echo WshShell.Run """%TARGET_DIR%\%EXE_NAME%""", 0, False >> "%STARTUP_DIR%\StorageMonitorClient.vbs"
wscript.exe "%STARTUP_DIR%\StorageMonitorClient.vbs"

echo.
echo ============================================================
echo  ✅ INSTALLAZIONE COMPLETATA!
echo  Il client e' attivo in background e si avviera'
echo  automaticamente ad ogni accensione del PC.
echo ============================================================
echo.
pause
