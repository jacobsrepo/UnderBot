@echo off
set "PIXI_CACHE_DIR=D:\Robotics\cache"
set "PIXI_HOME=D:\Robotics\tools\pixi-home"
"D:\Robotics\tools\pixi.exe" run --manifest-path "D:\Robotics\rviz2-jazzy\pixi.toml" python "D:\Robotics\compact-lab-rover\view_rover.py"
if errorlevel 1 pause
