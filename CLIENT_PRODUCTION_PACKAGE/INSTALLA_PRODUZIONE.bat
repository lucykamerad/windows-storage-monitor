@echo off
title Installatore Client Produzione Windows 11 Storage Monitor
color 0A
cls
echo ============================================================
echo   INSTALLATORE CLIENT WINDOWS STORAGE MONITOR (PRODUZIONE)
echo ============================================================
echo.

set TARGET_DIR=%LOCALAPPDATA%\WindowsStorageMonitor
set STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
set CSC_PATH=C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe

if not exist "%CSC_PATH%" (
    set CSC_PATH=C:\Windows\Microsoft.NET\Framework\v4.0.30319\csc.exe
)

if not exist "%CSC_PATH%" (
    echo [!] Errore: Compilatore Windows .NET non trovato su questo sistema.
    pause
    exit /b 1
)

echo [1/4] Creazione cartella di installazione in %TARGET_DIR%...
if not exist "%TARGET_DIR%" mkdir "%TARGET_DIR%"

set /p SERVER_URL="Indirizzo del server (es. http://192.168.1.100:8080): "
if "%SERVER_URL%"=="" set SERVER_URL=http://localhost:8080
>"%TARGET_DIR%\server_url.txt" echo %SERVER_URL%

echo [2/4] Compilazione eseguibile nativo invisibile in corso...
"%CSC_PATH%" /target:winexe /out:"%TARGET_DIR%\StorageMonitorClient.exe" /optimize "%~dp0StorageClientStatic.cs"

if not exist "%TARGET_DIR%\StorageMonitorClient.exe" (
    echo [!] Errore durante la compilazione dell'eseguibile.
    pause
    exit /b 1
)

echo [3/4] Configurazione avvio automatico all'accensione del PC (Startup)...
echo Set WshShell = CreateObject("WScript.Shell") > "%STARTUP_DIR%\StorageMonitorClient.vbs"
echo WshShell.Run """%TARGET_DIR%\StorageMonitorClient.exe""", 0, False >> "%STARTUP_DIR%\StorageMonitorClient.vbs"

echo [4/4] Avvio immediato del servizio in background...
wscript.exe "%STARTUP_DIR%\StorageMonitorClient.vbs"

echo.
echo ============================================================
echo  ✅ INSTALLAZIONE COMPLETATA CON SUCCESSO!
echo ============================================================
echo  • Percorso installazione: %TARGET_DIR%\StorageMonitorClient.exe
echo  • Server di destinazione: %SERVER_URL%
echo  • Avvio automatico: ATTIVATO ad ogni accensione del PC
echo  • Monitoraggio: Dischi fissi + Cartelle Temp / Cestino / Cache
echo ============================================================
echo.
pause
