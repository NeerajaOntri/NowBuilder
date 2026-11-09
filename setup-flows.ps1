# One-time preparation for deploying flows: downloads the ServiceNow SDK and signs it in to every
# connected Development/Test instance. Connect the instance in the app first. Safe to run again.
# Add -Reset to throw away a broken SDK download and start over.
param([switch]$Reset)
Set-Location "$PSScriptRoot\backend"
if (-not (Test-Path ".venv\Scripts\python.exe")) { Write-Host "Run .\setup.ps1 first." -ForegroundColor Red; exit 1 }
if ($Reset -and (Test-Path "data\sdk")) {
    Write-Host "Removing the old SDK download (data\sdk)..."
    Remove-Item -Recurse -Force "data\sdk"
}
& ".venv\Scripts\python.exe" -m app.sdk_setup
