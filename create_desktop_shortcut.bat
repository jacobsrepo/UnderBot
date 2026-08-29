@echo off
title Install Contender Desktop Shortcut
color 0b

echo ======================================================================
echo           CONTENDER - INSTALL DEDICATED DESKTOP SHORTCUT
echo ======================================================================
echo.

cd /d "%~dp0"

echo Creating Windows Desktop and Start Menu Shortcuts...
powershell -ExecutionPolicy Bypass -File "%~dp0create_desktop_shortcut.ps1"

echo.
echo [OK] Done! You can now launch Contender directly from your Desktop.
echo.
pause
