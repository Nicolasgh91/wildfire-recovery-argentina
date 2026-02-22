<#
.SYNOPSIS
  Runs Playwright UI smoke tests for ForestGuard.
.DESCRIPTION
  Validates that the frontend dev server is reachable, then runs
  `npm run test:ui` inside the frontend/ directory.
.PARAMETER BaseUrl
  Override default base URL (default: http://localhost:5173).
#>
param(
  [string]$BaseUrl = $env:PLAYWRIGHT_BASE_URL
)

if (-not $BaseUrl) { $BaseUrl = "http://localhost:5173" }

$ErrorActionPreference = "Stop"

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  ForestGuard UI Smoke Tests" -ForegroundColor Cyan
Write-Host "  Base URL: $BaseUrl" -ForegroundColor Cyan
Write-Host "========================================`n"

# -- Step 1: Ping frontend
Write-Host "1. Checking frontend is up..." -NoNewline
try {
  $response = Invoke-WebRequest -Uri $BaseUrl -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
  if ($response.StatusCode -eq 200) {
    Write-Host " OK (HTTP $($response.StatusCode))" -ForegroundColor Green
  }
} catch {
  Write-Host " FAILED" -ForegroundColor Red
  Write-Host "   The frontend is not running at $BaseUrl." -ForegroundColor Yellow
  Write-Host "   Start it with: cd frontend && npm run dev" -ForegroundColor Yellow
  exit 1
}

# -- Step 2: Run Playwright tests
Write-Host "`n2. Running Playwright tests...`n"
$env:PLAYWRIGHT_BASE_URL = $BaseUrl

Push-Location (Join-Path $PSScriptRoot "..\frontend")
try {
  npx playwright test --reporter=list
  $exitCode = $LASTEXITCODE
} finally {
  Pop-Location
}

# -- Step 3: Summary
Write-Host "`n========================================"
if ($exitCode -eq 0) {
  Write-Host "  ALL UI SMOKE TESTS PASSED" -ForegroundColor Green
} else {
  Write-Host "  SOME TESTS FAILED (exit code: $exitCode)" -ForegroundColor Red
  Write-Host "  Run with --headed for debug:" -ForegroundColor Yellow
  Write-Host "    cd frontend && npm run test:ui:headed" -ForegroundColor Yellow
}
Write-Host "========================================`n"

exit $exitCode
