# Start the local database and the private link; no camera capture is started here.
$ErrorActionPreference='Stop'
$root = Split-Path -Parent $PSScriptRoot
$env:PIXI_CACHE_DIR='D:\Robotics\cache'
Push-Location $root
try {
 & 'D:\Robotics\tools\pixi.exe' run python -m memory.bootstrap_windows
 if($LASTEXITCODE -ne 0){throw 'Database startup failed'}
 Start-Process -WindowStyle Hidden "$root\.pixi\envs\default\python.exe" -ArgumentList @('-u',"$PSScriptRoot\base_link.py") -WorkingDirectory $root
 Write-Host 'Base database and reconnecting Pi tunnel started.'
} finally {Pop-Location}
