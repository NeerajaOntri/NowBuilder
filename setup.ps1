# One-time setup for nowBuilder on Windows. Run from this folder:  .\setup.ps1
# Creates the backend virtual environment, installs Python and frontend packages,
# and makes backend\.env if there isn't one. Safe to run again.
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

Write-Host "== Checking Python and Node.js ==" -ForegroundColor Cyan
$py = $null
foreach ($v in @("-3.13", "-3.12")) {
    try { & py $v --version *> $null; if ($LASTEXITCODE -eq 0) { $py = @("py", $v); break } } catch {}
}
if (-not $py) {
    try { & python --version *> $null; if ($LASTEXITCODE -eq 0) { $py = @("python") } } catch {}
}
if (-not $py) { Write-Host "Python 3.12 or 3.13 is needed: install it from https://www.python.org/downloads/ and run this again." -ForegroundColor Red; exit 1 }
try { $node = (& node -v) } catch { $node = $null }
if (-not $node) { Write-Host "Node.js 20+ is needed: install the LTS from https://nodejs.org and reopen VS Code." -ForegroundColor Red; exit 1 }
$major = [int]($node.TrimStart("v").Split(".")[0])
if ($major -lt 20) { Write-Host "Node.js $node is too old: install the LTS (20 or later) from https://nodejs.org." -ForegroundColor Red; exit 1 }
Write-Host "Python: $($py -join ' ')   Node.js: $node"

Write-Host "`n== Backend ==" -ForegroundColor Cyan
Set-Location "$root\backend"
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    if ($py.Count -eq 2) { & $py[0] $py[1] -m venv .venv } else { & $py[0] -m venv .venv }
}
& ".venv\Scripts\python.exe" -m pip install --upgrade pip
& ".venv\Scripts\python.exe" -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { Write-Host "pip install failed (see above)." -ForegroundColor Red; exit 1 }
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    $keys = & ".venv\Scripts\python.exe" -m app.keys
    $content = Get-Content ".env"
    foreach ($line in $keys) {
        $name = $line.Split("=")[0]
        $content = $content -replace "^$name=.*$", $line
    }
    Set-Content ".env" $content
    Write-Host "Created backend\.env with new keys."
} else {
    Write-Host "Keeping the existing backend\.env (and its keys)."
}

Write-Host "`n== Frontend ==" -ForegroundColor Cyan
Set-Location "$root\frontend"
& npm install --no-audit --no-fund
if ($LASTEXITCODE -ne 0) { Write-Host "npm install failed (see above)." -ForegroundColor Red; exit 1 }

Set-Location $root
Write-Host "`nDone. Next:" -ForegroundColor Green
Write-Host "  1. .\start-backend.ps1     (terminal 1)"
Write-Host "  2. .\start-frontend.ps1    (terminal 2), then open http://localhost:5173"
Write-Host "  3. In the app: sign up, add the AI provider, connect your instance"
Write-Host "  4. .\setup-flows.ps1       (terminal 3, once: prepares flow deployment)"
