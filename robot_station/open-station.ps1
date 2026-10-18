param(
    [switch]$Live,
    [string]$RobotAddress = '100.123.136.69',
    [string]$FoxglovePath = 'D:\Foxglove\Foxglove.exe',
    [string]$PixiPath = 'pixi'
)
$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath $FoxglovePath -PathType Leaf)) {
    throw 'Specify -FoxglovePath with the path to your installed Foxglove.exe.'
}
Remove-Item Env:ELECTRON_RUN_AS_NODE -ErrorAction SilentlyContinue
if ($Live) {
    $endpoint = "ws://${RobotAddress}:8765"
} else {
    $endpoint = 'ws://127.0.0.1:8766'
    $listener = Get-NetTCPConnection -LocalPort 8766 -State Listen -ErrorAction SilentlyContinue
    if (-not $listener) {
        $pixiCommand = Get-Command $PixiPath -ErrorAction SilentlyContinue
        if (-not $pixiCommand) { throw 'Install Pixi or specify -PixiPath with the path to pixi.exe.' }
        $manifest = Join-Path $PSScriptRoot 'pixi.toml'
        $arguments = 'run --manifest-path "{0}" demo' -f $manifest
        Start-Process -WindowStyle Hidden -FilePath $pixiCommand.Source -ArgumentList $arguments -WorkingDirectory $PSScriptRoot -RedirectStandardOutput (Join-Path $PSScriptRoot 'demo.log') -RedirectStandardError (Join-Path $PSScriptRoot 'demo-errors.log')
        Write-Host 'Starting the demo. First run may take several minutes to download ROS dependencies.'
        Start-Sleep -Seconds 4
    }
}
Start-Process -FilePath $FoxglovePath -ArgumentList "foxglove://open?ds=foxglove-websocket&ds.url=$endpoint"
