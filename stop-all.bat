@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\stop_all.ps1" -StopContainers
if errorlevel 1 (
    echo.
    echo Shutdown encountered an error.
    pause
)
endlocal
