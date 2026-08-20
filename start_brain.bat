@echo off
title VLA Studio - Multimodal Vision and Voice Assistant
color 0f

echo ======================================================================
echo                  VLA STUDIO // LOCAL MULTIMODAL CORTEX
echo            Self-Contained Vision-Language-Action Architecture
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

echo [3/3] Starting Local and Network Server...
echo.
echo ----------------------------------------------------------------------
echo  Local Desktop Access:   https://localhost:8000
echo  Network Mobile Access:  https://192.168.0.26:8000
echo ----------------------------------------------------------------------
echo  (Open the Network URL on your phone or laptop on the same Wi-Fi)
echo.

:: Launch default browser
start https://localhost:8000/?v=%RANDOM%

"%PYTHON_EXE%" backend/app.py

pause
