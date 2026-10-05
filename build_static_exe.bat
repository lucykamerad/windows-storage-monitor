@echo off
title Compilatore EXE per Windows 11
color 0B
cls
echo ============================================================
echo   Compilatore EXE Windows Storage Monitor
echo ============================================================
echo.

set CSC_PATH=C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe

if not exist "%CSC_PATH%" (
    set CSC_PATH=C:\Windows\Microsoft.NET\Framework\v4.0.30319\csc.exe
)

if not exist "%CSC_PATH%" (
    echo [!] Errore: Compilatore .NET (csc.exe) non trovato su questo sistema.
    pause
    exit /b 1
)

echo Compilazione di StorageMonitorClient_Static.exe in corso...
"%CSC_PATH%" /target:exe /out:StorageMonitorClient_Static.exe /optimize StorageClientStatic.cs

if exist StorageMonitorClient_Static.exe (
    echo.
    echo ============================================================
    echo  ✅ ESEGUIBILE COMPILATO CON SUCCESSO!
    echo  📁 File creato: StorageMonitorClient_Static.exe
    echo ============================================================
    echo.
    echo Avvialo con l'indirizzo del server:  StorageMonitorClient_Static.exe http://IP-SERVER:8080
) else (
    echo [!] Errore durante la compilazione.
)

pause
