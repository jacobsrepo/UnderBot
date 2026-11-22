param([switch]$Headless, [switch]$PickPlace, [int]$Iterations = 1000)
$ErrorActionPreference = 'Stop'
$pixi = 'D:\Robotics\tools\pixi.exe'
$manifest = 'D:\Robotics\gazebo-harmonic\pixi.toml'
$env:PIXI_CACHE_DIR = 'D:\Robotics\cache'
$env:PIXI_HOME = 'D:\Robotics\tools\pixi-home'
$env:TEMP = 'D:\Robotics\downloads'
$env:TMP = $env:TEMP
$env:GZ_PARTITION = 'underbot-r09-native'
$env:GZ_FUEL_CACHE_PATH = 'D:\Robotics\gazebo-harmonic\fuel-cache'
New-Item -ItemType Directory -Force -Path $env:GZ_FUEL_CACHE_PATH | Out-Null
$python = Join-Path $PSScriptRoot '..\python\.venv\Scripts\python.exe'
$prepareArgs = @()
if ($PickPlace) { $prepareArgs += '--pick-place' }
& $python (Join-Path $PSScriptRoot 'prepare.py') @prepareArgs
if ($LASTEXITCODE -ne 0) { throw 'Model preparation failed' }
$world = Join-Path $PSScriptRoot 'generated\underbot_world.sdf'
if ($PickPlace) { $world = Join-Path $PSScriptRoot 'generated\pick_place_world.sdf' }
$gui = Join-Path $PSScriptRoot 'generated\gui.config'
$defaultGui = 'D:\Robotics\gazebo-harmonic\.pixi\envs\default\Library\share\gz\gz-sim8\gui\gui.config'
$guiText = Get-Content -LiteralPath $defaultGui -Raw
$guiText = $guiText -replace '<camera_pose>.*?</camera_pose>', '<camera_pose>-1.8 -1.8 1.4 0 0.35 0.7854</camera_pose>'
$guiText = $guiText -replace '<width>1000</width>', '<width>1280</width>'
Set-Content -LiteralPath $gui -Value $guiText -Encoding utf8
if ($Headless) {
    & $pixi run --manifest-path $manifest gz sim -s -r --iterations $Iterations -v 3 $world
    exit $LASTEXITCODE
}
# Harmonic on Windows requires separate server and GUI processes.
$server = Start-Process -WindowStyle Hidden -FilePath $pixi -ArgumentList @('run','--manifest-path',$manifest,'gz','sim','-s','-v','3',$world) -PassThru -RedirectStandardOutput (Join-Path $PSScriptRoot 'generated\server.log') -RedirectStandardError (Join-Path $PSScriptRoot 'generated\server-errors.log')
$controls = Start-Process -WindowStyle Hidden -FilePath (Join-Path $PSScriptRoot '..\python\.venv\Scripts\pythonw.exe') -ArgumentList ('"{0}"' -f (Join-Path $PSScriptRoot 'controls.py')) -PassThru -RedirectStandardOutput (Join-Path $PSScriptRoot 'generated\controls.log') -RedirectStandardError (Join-Path $PSScriptRoot 'generated\controls-errors.log')
try {
    & $pixi run --manifest-path $manifest gz sim -g -v 3 --gui-config $gui
} finally {
    if (-not $controls.HasExited) {
        & taskkill.exe /PID $controls.Id /T /F | Out-Null
    }
    if (-not $server.HasExited) {
        # Stop only the server process tree created by this launcher.
        & taskkill.exe /PID $server.Id /T /F | Out-Null
    }
}
