@echo off
chcp 65001 > nul
setlocal
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start_all.ps1"
if errorlevel 1 (
    echo.
    echo Startup failed. Check the error above and logs in .runtime.
    pause
)
endlocal
