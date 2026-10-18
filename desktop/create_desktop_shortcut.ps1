# Creates Windows Desktop and Start Menu shortcuts for Cortex AI
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$wscriptShell = New-Object -ComObject WScript.Shell

$desktopPath = [System.Environment]::GetFolderPath('Desktop')
$startMenuPath = [System.Environment]::GetFolderPath('StartMenu') + "\Programs"

# Desktop Shortcut
$shortcutPath = Join-Path $desktopPath "Cortex AI.lnk"
$shortcut = $wscriptShell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = Join-Path $scriptDir "start_brain.bat"
$shortcut.WorkingDirectory = $scriptDir
$shortcut.Description = "Cortex - AI Assistant & Hardware Engineer"
$shortcut.WindowStyle = 1
$shortcut.Save()
Write-Host "Created Desktop Shortcut: $shortcutPath"

# Start Menu Shortcut
$startMenuShortcutPath = Join-Path $startMenuPath "Cortex AI.lnk"
$startShortcut = $wscriptShell.CreateShortcut($startMenuShortcutPath)
$startShortcut.TargetPath = Join-Path $scriptDir "start_brain.bat"
$startShortcut.WorkingDirectory = $scriptDir
$startShortcut.Description = "Cortex - AI Assistant & Hardware Engineer"
$startShortcut.Save()
Write-Host "Created Start Menu Shortcut: $startMenuShortcutPath"
