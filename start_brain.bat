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

echo [2/3] Preparing Python Virtual Environment...
if exist ".venv\Scripts\python.exe" (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
) else (
    set "PYTHON_EXE=python"
)

echo [3/3] Starting Local Server...
echo.
echo ----------------------------------------------------------------------
echo  Interface URL:    http://localhost:8000
echo  Network Access:   http://0.0.0.0:8000
echo ----------------------------------------------------------------------
echo.

:: Launch default browser with cache-busting timestamp
start http://localhost:8000/?v=%RANDOM%

"%PYTHON_EXE%" -m uvicorn backend.app:app --host 0.0.0.0 --port 8000

pause
