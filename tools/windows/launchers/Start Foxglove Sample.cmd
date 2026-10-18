@echo off
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
"D:\Robotics\foxglove-demo\.venv\Scripts\python.exe" "D:\Robotics\foxglove-demo\stream.py"
if errorlevel 1 pause
