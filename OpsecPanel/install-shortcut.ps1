# Creates Desktop + Start Menu shortcuts for 66-Tool (current user only).
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$launchCmd = Join-Path $root "Launch-66-Tool.cmd"
$appCmd = Join-Path $root "Open-66-Tool-App.cmd"

function New-ToolShortcut([string]$Path, [string]$Target, [string]$Description) {
    $shell = New-Object -ComObject WScript.Shell
    $lnk = $shell.CreateShortcut($Path)
    $lnk.TargetPath = $Target
    $lnk.WorkingDirectory = $root
    $lnk.WindowStyle = 1
    $lnk.Description = $Description
    $icon = Join-Path $root "66-tool.ico"
    if (Test-Path $icon) {
        $lnk.IconLocation = "$icon,0"
    } else {
        $lnk.IconLocation = "$env:SystemRoot\System32\cmd.exe,0"
    }
    $lnk.Save()
}

$desktop = [Environment]::GetFolderPath("Desktop")
if (-not (Test-Path $desktop)) {
    throw "Desktop folder not found."
}

New-ToolShortcut (Join-Path $desktop "66 Tool.lnk") $launchCmd "66-Tool CMD privacy panel"
New-ToolShortcut (Join-Path $desktop "66 Tool Launcher.lnk") $appCmd "66-Tool launch button"

$programs = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"
if (Test-Path $programs) {
    New-ToolShortcut (Join-Path $programs "66 Tool.lnk") $launchCmd "66-Tool CMD privacy panel"
}

Write-Host "Shortcuts created:"
Write-Host "  $desktop\66 Tool.lnk"
Write-Host "  $desktop\66 Tool Launcher.lnk"
Write-Host "Right-click a shortcut and Pin to taskbar if you want it on the bar."
