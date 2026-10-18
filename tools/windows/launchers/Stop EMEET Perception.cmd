@echo off
set "PIXI_CACHE_DIR=D:\Robotics\cache"
set "PIXI_HOME=D:\Robotics\tools\pixi-home"
"D:\Robotics\tools\pixi.exe" run --manifest-path "D:\gitdemo\Underbot\.publish-underbot\perception\pixi.toml" stop
