# Starts the nowBuilder web app on http://localhost:5173 (keep this terminal open).
Set-Location "$PSScriptRoot\frontend"
if (-not (Test-Path "node_modules")) { Write-Host "Run .\setup.ps1 first." -ForegroundColor Red; exit 1 }
& npm run dev
