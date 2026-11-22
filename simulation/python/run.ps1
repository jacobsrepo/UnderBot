param([switch]$Headless)
$ErrorActionPreference = 'Stop'
$pythonExe = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonExe)) {
    throw 'Create the simulation .venv first; see README.md.'
}
$arguments = @((Join-Path $PSScriptRoot 'simulator.py'))
if (-not $Headless) { $arguments += '--gui' }
& $pythonExe @arguments
exit $LASTEXITCODE
