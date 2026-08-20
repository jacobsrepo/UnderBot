@echo off
title VLA Studio - Multimodal Vision and Voice Assistant
color 0f
echo ======================================================================
echo                  VLA STUDIO // LOCAL MULTIMODAL CORTEX
echo            Self-Contained Vision-Language-Action Architecture
echo ======================================================================
echo.

cd /d "%~dp0"

echo [1/2] Checking Python Virtual Environment...
if exist ".venv\Scripts\python.exe" (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
) else (
    set "PYTHON_EXE=python"
)

echo [2/2] Starting Local Server...
echo.
echo ----------------------------------------------------------------------
echo  Interface URL:    http://localhost:8000
echo  Network Access:   http://0.0.0.0:8000
echo ----------------------------------------------------------------------
echo.

start http://localhost:8000

"%PYTHON_EXE%" -m uvicorn backend.app:app --host 0.0.0.0 --port 8000

pause
