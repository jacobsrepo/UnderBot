$ErrorActionPreference = 'Stop'
$python = Join-Path $PSScriptRoot '..\python\.venv\Scripts\pythonw.exe'
Start-Process -WindowStyle Hidden -FilePath $python -ArgumentList ('"{0}"' -f (Join-Path $PSScriptRoot 'controls.py')) -WorkingDirectory $PSScriptRoot
