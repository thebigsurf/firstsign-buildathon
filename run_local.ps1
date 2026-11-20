# Builds the frontend if needed and serves app + API on http://localhost:8000.
# Usage: .\run_local.ps1        (set $env:DEMO_OFFLINE=1 first to use canned results without Gemini)
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$port = if ($env:PORT) { $env:PORT } else { "8000" }
if (-not (Test-Path "$root\frontend\dist\index.html")) {
    Write-Host "Building frontend..."
    Push-Location "$root\frontend"
    npm ci --no-audit --no-fund
    if ($LASTEXITCODE -eq 0) { npm run build }
    $code = $LASTEXITCODE
    Pop-Location
    if ($code -ne 0) { throw "Frontend build failed" }
}
python -m pip install -q -r "$root\backend\requirements.txt"
Set-Location "$root\backend"
Write-Host "FirstSign on http://localhost:$port"
python -m uvicorn app.main:app --host 127.0.0.1 --port $port
