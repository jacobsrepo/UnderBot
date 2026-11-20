# Start the complete local dashboard; microphone capture remains operator-controlled.
param(
    [string]$RosPrefix = 'D:\Robotics\rviz2-jazzy\.pixi\envs\default',
    [string]$FoxglovePath = 'D:\Foxglove\Foxglove.exe',
    [int]$Port = 8767,
    [switch]$NoOpen
)
$ErrorActionPreference = 'Stop'
$stationRoot = $PSScriptRoot
$perceptionRoot = Join-Path (Split-Path $stationRoot -Parent) 'perception'
$perceptionPrefix = Join-Path $perceptionRoot '.pixi\envs\default'
$perceptionPython = Join-Path $perceptionPrefix 'python.exe'
$edgeConfig = Join-Path $perceptionRoot '.private\edge-test.json'
$pgData = Join-Path $perceptionRoot '.private\pgdata'
$pgCtl = 'C:\Program Files\PostgreSQL\18\bin\pg_ctl.exe'
foreach ($required in @($perceptionPython, $edgeConfig, $pgCtl, (Join-Path $pgData 'PG_VERSION'))) {
    if (-not (Test-Path -LiteralPath $required)) { throw "Existing live setup missing: $required" }
}
$env:ROS_LOG_DIR = Join-Path $env:TEMP 'underbot-fleet-ros-logs'
$env:RMW_IMPLEMENTATION = 'rmw_cyclonedds_cpp'
$env:CYCLONEDDS_URI = '<CycloneDDS><Domain><General><Interfaces><NetworkInterface address="127.0.0.1"/></Interfaces><AllowMulticast>false</AllowMulticast></General></Domain></CycloneDDS>'
$env:PATH = "$perceptionPrefix\Library\bin;$perceptionPrefix\Library\lib;$perceptionPrefix;$env:PATH"
$env:AMENT_PREFIX_PATH = "$perceptionPrefix\Library"
$running = @(Get-CimInstance Win32_Process -Filter "name='python.exe'")
function Start-PerceptionService($script, $arguments, $logName) {
    $scriptPath = Join-Path $perceptionRoot $script
    $existing = @($running | Where-Object { $_.CommandLine -like "*$scriptPath*" })
    if ($existing.Count) {
        if ($script -in @('start.py', 'pi_comms.py') -and ($existing | Where-Object { $_.CommandLine -notmatch '--domain\s+75\b' })) {
            throw "$script is already running on another ROS domain. Stop that pipeline before starting fleet live."
        }
        return
    }
    Start-Process -WindowStyle Hidden $perceptionPython -ArgumentList (@('-u', ('"'+$scriptPath+'"')) + $arguments) -WorkingDirectory $perceptionRoot -RedirectStandardOutput "$perceptionRoot\$logName.log" -RedirectStandardError "$perceptionRoot\$logName-errors.log"
}
& $pgCtl -D $pgData status | Out-Null
if ($LASTEXITCODE -ne 0) {
    & $pgCtl -D $pgData -l (Join-Path $perceptionRoot '.private\postgres.log') -o '-p 55432 -h 127.0.0.1' -w start
    if ($LASTEXITCODE -ne 0) { throw 'Recognition database did not start.' }
}
Start-PerceptionService 'memory\base_link.py' @() 'fleet-link'
Start-PerceptionService 'start.py' @('--domain','75','--memory-config',('"'+$edgeConfig+'"')) 'fleet-live'
Start-PerceptionService 'pi_comms.py' @('--domain','75') 'fleet-comms'
if (-not (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)) {
    Start-Process -WindowStyle Hidden powershell.exe -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-File',('"'+$stationRoot+'\open-fleet.ps1"'),'-RosPrefix',('"'+$RosPrefix+'"'),'-Port',$Port) -WorkingDirectory $stationRoot -RedirectStandardOutput "$stationRoot\fleet.log" -RedirectStandardError "$stationRoot\fleet-errors.log"
}
$deadline = (Get-Date).AddSeconds(30)
while (-not (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)) {
    if ((Get-Date) -gt $deadline) { throw 'Fleet bridge did not start; inspect robot_station/fleet-errors.log.' }
    Start-Sleep -Milliseconds 500
}
if (-not $NoOpen) {
    Remove-Item Env:ELECTRON_RUN_AS_NODE -ErrorAction SilentlyContinue
    Start-Process $FoxglovePath -ArgumentList "foxglove://open?ds=foxglove-websocket&ds.url=ws://127.0.0.1:$Port"
}
Write-Host "Fleet + live camera/recognition started at ws://127.0.0.1:$Port (ROS domain 75)."
Write-Host 'AI uses the existing Pi tunnel; the Pi must be online. Microphone capture is off until requested.'
