# Starts the nowBuilder backend on http://localhost:8000 (keep this terminal open).
# Auto-reload watches only the app code: the ServiceNow SDK download writes thousands of files under
# backend\data, and reloading on those would restart the backend in the middle of the download.
Set-Location "$PSScriptRoot\backend"
if (-not (Test-Path ".venv\Scripts\python.exe")) { Write-Host "Run .\setup.ps1 first." -ForegroundColor Red; exit 1 }
& ".venv\Scripts\python.exe" -m uvicorn app.main:app --reload --reload-dir app
