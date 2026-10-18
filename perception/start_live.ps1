param([switch]$Microphone)
$ErrorActionPreference='Stop'
$root=$PSScriptRoot
$pixi='D:\Robotics\tools\pixi.exe'
$env:PIXI_CACHE_DIR='D:\Robotics\cache'
$env:PIXI_HOME='D:\Robotics\tools\pixi-home'
$env:RMW_IMPLEMENTATION='rmw_cyclonedds_cpp'
$env:CYCLONEDDS_URI='<CycloneDDS><Domain><General><Interfaces><NetworkInterface address="127.0.0.1"/></Interfaces><AllowMulticast>false</AllowMulticast></General></Domain></CycloneDDS>'
& "$root\memory\start_base.ps1"
$listener=Get-NetTCPConnection -LocalPort 8766 -State Listen -ErrorAction SilentlyContinue
if(-not $listener){
 Start-Process -WindowStyle Hidden $pixi -ArgumentList @('run','--manifest-path','D:\Robotics\rviz2-jazzy\pixi.toml','python','D:\Robotics\robot-station\start.py','--demo','--navigation-demo','--port','8766','--ai-url','http://127.0.0.1:11435','--memory-python',"$root\.pixi\envs\default\python.exe",'--memory-config',"$root\.private\base.json") -WorkingDirectory 'D:\Robotics\robot-station' -RedirectStandardOutput 'D:\Robotics\robot-station\demo.log' -RedirectStandardError 'D:\Robotics\robot-station\demo-errors.log'
}
$processes=Get-CimInstance Win32_Process -Filter "name='python.exe'" | Where-Object { $_.ExecutablePath -eq "$root\.pixi\envs\default\python.exe" }
if(-not ($processes | Where-Object { $_.CommandLine -match 'pi_comms\.py' })){
 Start-Process -WindowStyle Hidden $pixi -ArgumentList @('run','--manifest-path',('"'+$root+'\pixi.toml"'),'python','pi_comms.py') -WorkingDirectory $root -RedirectStandardOutput "$root\comms.log" -RedirectStandardError "$root\comms-errors.log"
}
if(-not ($processes | Where-Object { $_.CommandLine -match '(^|[\\\s\"])start\.py([\s\"]|$)' })){
 Start-Process -WindowStyle Hidden $pixi -ArgumentList @('run','--manifest-path',('"'+$root+'\pixi.toml"'),'start','--memory-config',('"'+$root+'\.private\edge-test.json"')) -WorkingDirectory $root -RedirectStandardOutput "$root\live.log" -RedirectStandardError "$root\live-errors.log"
}
if($Microphone -and -not ($processes | Where-Object { $_.CommandLine -match 'audio_node\.py' })){
 Write-Host 'Starting live headset microphone. Panel mute controls playback; use Stop Headset Mic.cmd to stop capture.'
 Start-Process -WindowStyle Hidden $pixi -ArgumentList @('run','--manifest-path',('"'+$root+'\pixi.toml"'),'audio') -WorkingDirectory $root -RedirectStandardOutput "$root\audio.log" -RedirectStandardError "$root\audio-errors.log"
}
$deadline=(Get-Date).AddSeconds(45)
do {
 $listener=Get-NetTCPConnection -LocalPort 8766 -State Listen -ErrorAction SilentlyContinue
 if($listener){break}
 Start-Sleep -Milliseconds 500
} while((Get-Date) -lt $deadline)
if(-not $listener){throw 'Foxglove bridge did not start. Check D:\Robotics\robot-station\demo-errors.log'}
Remove-Item Env:ELECTRON_RUN_AS_NODE -ErrorAction SilentlyContinue
Start-Process 'D:\Foxglove\Foxglove.exe' -ArgumentList 'foxglove://open?ds=foxglove-websocket&ds.url=ws://127.0.0.1:8766'
Write-Host 'EMEET Live services are running. Select UnderBot EMEET Live if Foxglove opens another layout.'
Write-Host 'Camera/mic are real. Room map, motion and IMU are synthetic demo data; geographic position is a manual marker.'
