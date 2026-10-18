$ErrorActionPreference = 'Stop'
$archive = Join-Path $env:TEMP 'underbot-station-deploy.tar.gz'
tar -czf $archive --exclude=__pycache__ --exclude=*.pyc -C $PSScriptRoot .
if ($LASTEXITCODE -ne 0) { throw 'Could not create station archive' }
$payload = [Convert]::ToBase64String([IO.File]::ReadAllBytes($archive))
# Fixed deployment directory, base64 payload contains no shell metacharacters.
$remoteCommand = "mkdir -p ~/underbot-station && printf '%s' '$payload' | base64 -d | tar -xzf - -C ~/underbot-station && bash ~/underbot-station/setup_pi.sh"
Write-Host 'Sign in to underbot@100.123.136.69 when prompted. Enter passwords only in this window.'
ssh -tt -o StrictHostKeyChecking=yes underbot@100.123.136.69 $remoteCommand
if ($LASTEXITCODE -ne 0) { throw 'Pi setup did not complete. Review the SSH output above.' }
Write-Host 'Pi station is ready. Connect Foxglove to ws://100.123.136.69:8765.'
Read-Host 'Press Enter to close'
