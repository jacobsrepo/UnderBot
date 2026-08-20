@echo off
title AURA Vision & Voice Assistant
color 0f
echo ======================================================================
echo                  AURA VISION & VOICE ASSISTANT
echo         Universal Multimodal Cognitive Studio (v2.0)
echo ======================================================================
echo.

cd /d "%~dp0"

echo [1/2] Checking Python Virtual Environment...
if exist ".venv\Scripts\python.exe" (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
) else (
    set "PYTHON_EXE=python"
)

echo [2/2] Launching Universal Server (FastAPI + WebSockets)...
echo.
echo ----------------------------------------------------------------------
echo  Local Interface:   http://localhost:8000
echo  Network Access:    http://0.0.0.0:8000 (Open on phone/laptop)
echo ----------------------------------------------------------------------
echo.

start http://localhost:8000

"%PYTHON_EXE%" -m uvicorn backend.app:app --host 0.0.0.0 --port 8000

pause
