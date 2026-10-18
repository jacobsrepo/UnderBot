@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File D:\gitdemo\Underbot\.publish-underbot\perception\start_live.ps1 -Microphone
if errorlevel 1 pause
