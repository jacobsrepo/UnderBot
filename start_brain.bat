@echo off
title Local Robot Brain - Neural Sensory Cortex
color 0b
echo ======================================================================
echo          LOCAL ROBOT BRAIN // NEURAL SENSORY CORTEX
echo    Vision-Language-Action Live Multimodal Cockpit (RTX 3050)
echo ======================================================================
echo.

cd /d "%~dp0"

echo [1/3] Checking Ollama Service...
curl -s http://127.0.0.1:11434/api/tags >nul 2>&1
if %errorlevel% neq 0 (
    echo Ollama is not responding on port 11434. Trying to locate and launch Ollama...
    
    REM Check if ollama command is in PATH
    where ollama >nul 2>&1
    if %errorlevel% equ 0 (
        start "" ollama serve
        goto :wait_ollama
    )
    
    REM Check Local AppData Programs
    if exist "%LOCALAPPDATA%\Programs\Ollama\ollama app.exe" (
        start "" "%LOCALAPPDATA%\Programs\Ollama\ollama app.exe"
        goto :wait_ollama
    )
    if exist "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" (
        start "" "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" serve
        goto :wait_ollama
    )
    if exist "%ProgramFiles%\Ollama\ollama.exe" (
        start "" "%ProgramFiles%\Ollama\ollama.exe" serve
        goto :wait_ollama
    )
    
    echo.
    echo [INFO] Ollama launcher not in standard path.
    echo Please make sure Ollama is launched from your Start Menu if you want local LLM vision inference.
    echo Continuing to start Sensory Server...
    goto :proceed_app

:wait_ollama
    echo Waiting 3 seconds for Ollama to initialize...
    timeout /t 3 /nobreak >nul
) else (
    echo [OK] Ollama is active and online.
)

:proceed_app
echo.
echo [2/3] Activating Python Virtual Environment...
if exist ".venv\Scripts\python.exe" (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
) else (
    set "PYTHON_EXE=python"
)

echo.
echo [3/3] Launching Sensory Cortex Server (FastAPI + WebSockets)...
echo Opening interface at: http://localhost:8000
echo.

start http://localhost:8000

"%PYTHON_EXE%" -m uvicorn backend.app:app --host 0.0.0.0 --port 8000

pause
