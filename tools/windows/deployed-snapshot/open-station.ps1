param([switch]$Live)
$ErrorActionPreference='Stop'
Remove-Item Env:ELECTRON_RUN_AS_NODE -ErrorAction SilentlyContinue
if ($Live) {
    $endpoint='ws://100.123.136.69:8765'
} else {
    $endpoint='ws://127.0.0.1:8766'
    $listener=Get-NetTCPConnection -LocalPort 8766 -State Listen -ErrorAction SilentlyContinue
    if (-not $listener) {
        $env:PIXI_CACHE_DIR='D:\Robotics\cache'
        $env:PIXI_HOME='D:\Robotics\tools\pixi-home'
        Start-Process -WindowStyle Hidden -FilePath 'D:\Robotics\tools\pixi.exe' -ArgumentList @('run','--manifest-path','D:\Robotics\rviz2-jazzy\pixi.toml','python','D:\Robotics\robot-station\start.py','--demo','--navigation-demo','--port','8766','--ai-url','http://127.0.0.1:11435','--memory-python','D:\gitdemo\Underbot\.publish-underbot\perception\.pixi\envs\default\python.exe','--memory-config','D:\gitdemo\Underbot\.publish-underbot\perception\.private\base.json') -RedirectStandardOutput 'D:\Robotics\robot-station\demo.log' -RedirectStandardError 'D:\Robotics\robot-station\demo-errors.log'
        Start-Sleep -Seconds 4
    }
}
Start-Process 'D:\Foxglove\Foxglove.exe' -ArgumentList "foxglove://open?ds=foxglove-websocket&ds.url=$endpoint"
