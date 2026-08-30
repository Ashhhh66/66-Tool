$root = (Resolve-Path $PSScriptRoot).Path.TrimEnd("\")
$user = [Environment]::GetEnvironmentVariable("Path", "User")
if ($null -eq $user) {
    $user = ""
}
$parts = @($user -split ";" | Where-Object { $_ -ne "" })
if ($parts -contains $root) {
    Write-Host "66-Tool is already on your user PATH."
    Write-Host "Open a new Command Prompt and run: 66-tool -h"
    exit 0
}
[Environment]::SetEnvironmentVariable("Path", ($parts + $root) -join ";", "User")
Write-Host "Added $root to your user PATH."
Write-Host "Open a new Command Prompt, then run: 66-tool -h"
