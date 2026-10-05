@echo off
title Build Executable .exe Windows 11
color 0B
cls
echo ============================================================
echo   Compilatore Eseguibile Windows Storage Monitor (.exe)
echo ============================================================
echo.

echo Installazione PyInstaller...
pip install pyinstaller

echo Compilazione dell'applicazione GUI in win_client_gui.exe...
pyinstaller --noconsole --onefile --name "StorageMonitorClient" win_client_gui.py

echo.
if exist "dist\StorageMonitorClient.exe" (
    echo ============================================================
    echo  ✅ ESEGUIBILE COMPILATO CON SUCCESSO!
    echo  📁 Trovi il file in: dist\StorageMonitorClient.exe
    echo ============================================================
) else (
    echo ============================================================
    echo  ❌ ERRORE: Compilazione fallita!
    echo  Assicurati che Python e Pip siano installati e aggiunti al PATH.
    echo ============================================================
)
pause

