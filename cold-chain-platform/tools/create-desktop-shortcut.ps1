$ErrorActionPreference = "Stop"

$projectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$desktopAppDir = Join-Path $projectRoot "desktop"
$packagedExe = Join-Path $desktopAppDir "dist\win-unpacked\Cold Chain Platform.exe"
$launcher = Join-Path $desktopAppDir "start-cold-chain-desktop.cmd"
$shortcutPath = Join-Path ([Environment]::GetFolderPath("Desktop")) "Cold Chain Platform.lnk"

if (Test-Path $packagedExe) {
  $target = $packagedExe
  $workingDirectory = Split-Path $packagedExe -Parent
} elseif (Test-Path $launcher) {
  $target = $launcher
  $workingDirectory = $desktopAppDir
} else {
  throw "Launcher not found: $launcher"
}

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $target
$shortcut.WorkingDirectory = $workingDirectory
$shortcut.WindowStyle = 1
$shortcut.Description = "Start Cold Chain Platform Desktop"
$shortcut.Save()

Write-Host "Desktop shortcut created: $shortcutPath"
