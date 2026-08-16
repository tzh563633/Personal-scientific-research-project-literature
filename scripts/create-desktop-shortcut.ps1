param(
  [string]$ShortcutName
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$desktop = [Environment]::GetFolderPath("Desktop")
$platformName = -join ([char[]](0x79D1, 0x7814, 0x63A7, 0x5236, 0x5E73, 0x53F0))
if ([string]::IsNullOrWhiteSpace($ShortcutName)) {
  $ShortcutName = "$platformName.lnk"
}
$shortcutPath = Join-Path $desktop $ShortcutName
$powershell = (Get-Command powershell.exe).Source
$launcher = Join-Path $root "scripts\start-platform.ps1"

if (-not (Test-Path -LiteralPath $launcher)) {
  throw "Platform launcher was not found: $launcher"
}

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $powershell
$shortcut.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$launcher`""
$shortcut.WorkingDirectory = $root
$shortcut.Description = "Start $platformName"
$shortcut.IconLocation = "$env:SystemRoot\System32\SHELL32.dll,220"
$shortcut.Save()

Write-Host "Desktop shortcut created: $shortcutPath"
