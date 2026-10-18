@echo off
set PIXI_CACHE_DIR=D:\Robotics\cache
cd /d D:\gitdemo\Underbot\.publish-underbot\perception
D:\Robotics\tools\pixi.exe run python -m memory.bootstrap_windows
if errorlevel 1 goto done
D:\Robotics\tools\pixi.exe run start --memory-config .private/edge-test.json
:done
pause
