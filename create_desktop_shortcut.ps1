# Creates Windows Desktop and Start Menu shortcuts for Contender AI
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$wscriptShell = New-Object -ComObject WScript.Shell

$desktopPath = [System.Environment]::GetFolderPath('Desktop')
$startMenuPath = [System.Environment]::GetFolderPath('StartMenu') + "\Programs"

# Desktop Shortcut
$shortcutPath = Join-Path $desktopPath "Contender AI.lnk"
$shortcut = $wscriptShell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = Join-Path $scriptDir "start_brain.bat"
$shortcut.WorkingDirectory = $scriptDir
$shortcut.Description = "Contender - Tactical Desktop Assistant & Hardware Engineer"
$shortcut.WindowStyle = 1
$shortcut.Save()
Write-Host "Created Desktop Shortcut: $shortcutPath"

# Start Menu Shortcut
$startMenuShortcutPath = Join-Path $startMenuPath "Contender AI.lnk"
$startShortcut = $wscriptShell.CreateShortcut($startMenuShortcutPath)
$startShortcut.TargetPath = Join-Path $scriptDir "start_brain.bat"
$startShortcut.WorkingDirectory = $scriptDir
$startShortcut.Description = "Contender - Tactical Desktop Assistant & Hardware Engineer"
$startShortcut.Save()
Write-Host "Created Start Menu Shortcut: $startMenuShortcutPath"
