param(
    [string]$RobotAddress = '100.123.136.69',
    [string]$RobotUser = 'underbot'
)
$ErrorActionPreference = 'Stop'
if ($RobotAddress -notmatch '^[A-Za-z0-9][A-Za-z0-9.-]*$' -or $RobotUser -notmatch '^[a-z_][a-z0-9_-]*$') {
    throw 'Use an IPv4 address or hostname and a Linux username.'
}
$target = "${RobotUser}@${RobotAddress}"
Write-Host "Deploying to $target. Enter passwords only in SSH prompts."
# Copy a bounded file list, without logs, caches, binaries or command-line payload limits.
ssh -o StrictHostKeyChecking=ask $target 'mkdir -p ~/underbot-station'
if ($LASTEXITCODE -ne 0) { throw 'SSH connection failed.' }
$names = @('start.py','gateway.py','demo.py','bridge.yaml','setup_pi.sh')
$files = $names | ForEach-Object { Join-Path $PSScriptRoot $_ }
scp -o StrictHostKeyChecking=yes @files "${target}:underbot-station/"
if ($LASTEXITCODE -ne 0) { throw 'Copy to Pi failed.' }
ssh -tt -o StrictHostKeyChecking=yes $target "bash ~/underbot-station/setup_pi.sh $RobotAddress"
if ($LASTEXITCODE -ne 0) { throw 'Pi setup did not complete. Review the SSH output above.' }
Write-Host "Pi station is ready. Connect Foxglove to ws://${RobotAddress}:8765."
