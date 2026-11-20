param(
    [string]$RosPrefix = 'D:\Robotics\rviz2-jazzy\.pixi\envs\default',
    [int]$Port = 8767,
    [string]$AiUrl = 'http://127.0.0.1:11435'
)
$ErrorActionPreference = 'Stop'
$fleetPython = Join-Path $RosPrefix 'python.exe'
if (-not (Test-Path -LiteralPath $fleetPython)) {
    throw 'Specify -RosPrefix pointing to an installed RoboStack environment.'
}
$env:PATH = "$RosPrefix\Library\bin;$RosPrefix\Library\lib;$RosPrefix;$env:PATH"
$env:AMENT_PREFIX_PATH = "$RosPrefix\Library"
$env:ROS_DISTRO = 'jazzy'
$env:ROS_VERSION = '2'
$env:ROS_PYTHON_VERSION = '3'
$env:ROS_LOG_DIR = Join-Path $env:TEMP 'underbot-fleet-ros-logs'
Write-Host "Fleet simulation: connect Foxglove to ws://127.0.0.1:$Port"
Write-Host 'Import navigation/underbot-fleet-layout.json. Press Ctrl+C to stop.'
$perceptionRoot = Join-Path (Split-Path $PSScriptRoot -Parent) 'perception'
$fleetArguments = @((Join-Path $PSScriptRoot 'start.py'), '--demo', '--fleet-demo', '--port', $Port, '--ai-url', $AiUrl)
$memoryPython = Join-Path $perceptionRoot '.pixi\envs\default\python.exe'
$memoryConfig = Join-Path $perceptionRoot '.private\base.json'
if ((Test-Path -LiteralPath $memoryPython) -and (Test-Path -LiteralPath $memoryConfig)) {
    $fleetArguments += @('--memory-python', $memoryPython, '--memory-config', $memoryConfig)
}
& $fleetPython @fleetArguments
exit $LASTEXITCODE
