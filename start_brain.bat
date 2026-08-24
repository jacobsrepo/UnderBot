@echo off
title Contender - Tactical Desktop Studio
color 0b

echo ======================================================================
echo                 CONTENDER // TACTICAL DESKTOP ASSISTANT
echo        Continuous Screen Perception, Hardware ^& Desktop Automation
echo ======================================================================
echo.

cd /d "%~dp0"

echo [1/3] Terminating any conflicting background server instances...
powershell -Command "Get-NetTCPConnection -LocalPort 8000,8001 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }" >nul 2>&1

echo [2/3] Preparing Python Virtual Environment and Network Certificates...
if exist ".venv\Scripts\python.exe" (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
) else (
    set "PYTHON_EXE=python"
)

:: Generate SSL certs if missing
"%PYTHON_EXE%" -c "from backend.ssl_helper import ensure_ssl_certificates; ensure_ssl_certificates('certs')" >nul 2>&1

echo [3/3] Launching Contender Native Tactical Studio...
echo.
echo ----------------------------------------------------------------------
echo  Desktop Studio:     http://localhost:8000
echo  Mobile / LAN Feed:  https://192.168.0.26:8000
echo ----------------------------------------------------------------------
echo.

:: Launch Desktop Shell
"%PYTHON_EXE%" desktop_shell.py

pause
