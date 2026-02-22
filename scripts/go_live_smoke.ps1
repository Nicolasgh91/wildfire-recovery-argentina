# =============================================================================
# ForestGuard Go-Live Smoke Test Script
# =============================================================================
#
# Automated validation script for go-live readiness.
# Tests: health checks, feature flags, GCS connectivity (optional), Celery (optional)
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts/go_live_smoke.ps1
#
# Exit codes:
#   0 - All critical tests passed
#   1 - One or more critical tests failed
#
# =============================================================================

$ErrorActionPreference = "Continue"
$BASE_URL = "http://localhost:8000"
$PASSED = 0
$FAILED = 0
$WARNINGS = 0

Write-Host "========================================"
Write-Host "  ForestGuard Go-Live Smoke Tests"
Write-Host "  Base URL: $BASE_URL"
Write-Host "========================================"
Write-Host ""

# Helper function to test an endpoint
function Test-Endpoint {
    param(
        [string]$Name,
        [string]$Url,
        [int]$ExpectedStatus = 200
    )
    
    Write-Host -NoNewline "Testing: $Name... "
    
    try {
        $response = Invoke-WebRequest -Uri $Url -Method GET -UseBasicParsing -TimeoutSec 10 -ErrorAction Stop
        $status = $response.StatusCode
        
        if ($status -eq $ExpectedStatus) {
            Write-Host "PASSED" -ForegroundColor Green -NoNewline
            Write-Host " (HTTP $status)"
            $script:PASSED++
            return $true
        } else {
            Write-Host "FAILED" -ForegroundColor Red -NoNewline
            Write-Host " (expected $ExpectedStatus, got $status)"
            $script:FAILED++
            return $false
        }
    } catch {
        $status = $_.Exception.Response.StatusCode.value__
        if ($null -eq $status) {
            Write-Host "FAILED" -ForegroundColor Red -NoNewline
            Write-Host " (connection error: $($_.Exception.Message))"
            $script:FAILED++
            return $false
        }
        
        if ($status -eq $ExpectedStatus) {
            Write-Host "PASSED" -ForegroundColor Green -NoNewline
            Write-Host " (HTTP $status)"
            $script:PASSED++
            return $true
        } else {
            Write-Host "FAILED" -ForegroundColor Red -NoNewline
            Write-Host " (expected $ExpectedStatus, got $status)"
            $script:FAILED++
            return $false
        }
    }
}

# =============================================================================
# 1. Health Checks (CRITICAL)
# =============================================================================
Write-Host "=== 1. Health Checks (CRITICAL) ===" -ForegroundColor Cyan
Test-Endpoint "Root health" "$BASE_URL/health" 200
Test-Endpoint "Database health" "$BASE_URL/api/v1/health/db" 200
Test-Endpoint "Celery health" "$BASE_URL/api/v1/health/celery" 200
Test-Endpoint "GEE health" "$BASE_URL/api/v1/health/gee" 200
Write-Host ""

# =============================================================================
# 2. Feature Flags Enforcement (CRITICAL)
# =============================================================================
Write-Host "=== 2. Feature Flags Enforcement (CRITICAL) ===" -ForegroundColor Cyan
Test-Endpoint "Certificates blocked" "$BASE_URL/api/v1/certificates/verify/test" 404
Test-Endpoint "Visitor logs blocked" "$BASE_URL/api/v1/visitor-logs" 404
Test-Endpoint "Shelters blocked" "$BASE_URL/api/v1/shelters" 404
Write-Host ""

# =============================================================================
# 3. GCS Connectivity (OPTIONAL - requires credentials)
# =============================================================================
Write-Host "=== 3. GCS Connectivity (OPTIONAL) ===" -ForegroundColor Cyan

if ($env:SKIP_GCS -eq "1") {
    Write-Host "SKIPPED (SKIP_GCS=1)" -ForegroundColor Yellow
    $script:WARNINGS++
    Write-Host ""
} else {
    Write-Host -NoNewline "Running GCS test script... "

    if (Test-Path "scripts/test_gcs_conn.py") {
        try {
            $gcsResult = python scripts/test_gcs_conn.py 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Host "PASSED" -ForegroundColor Green
                $script:PASSED++
                
                # Check if report was generated
                if (Test-Path "artifacts/gcs_conn_report.json") {
                    Write-Host "  Report: artifacts/gcs_conn_report.json" -ForegroundColor Gray
                }
            } else {
                Write-Host "FAILED" -ForegroundColor Yellow -NoNewline
                Write-Host " (see output above for details)"
                $script:WARNINGS++
                Write-Host "  Note: GCS test requires valid credentials" -ForegroundColor Gray
            }
        } catch {
            Write-Host "SKIPPED" -ForegroundColor Yellow -NoNewline
            Write-Host " (error running script: $($_.Exception.Message))"
            $script:WARNINGS++
        }
    } else {
        Write-Host "SKIPPED" -ForegroundColor Yellow -NoNewline
        Write-Host " (test_gcs_conn.py not found)"
        $script:WARNINGS++
    }
    Write-Host ""
}

# =============================================================================
# 4. Celery Workers (OPTIONAL - requires Redis)
# =============================================================================
Write-Host "=== 4. Celery Workers (OPTIONAL) ===" -ForegroundColor Cyan
Write-Host -NoNewline "Checking Celery broker... "

# The /api/v1/health/celery endpoint already tests Redis connectivity
# We already tested it above, so just note the result
Write-Host "See health check above" -ForegroundColor Gray
Write-Host ""

# =============================================================================
# Summary
# =============================================================================
Write-Host "========================================"
Write-Host "  RESULTS"
Write-Host "========================================"
Write-Host "  Passed:   " -NoNewline
Write-Host $PASSED -ForegroundColor Green
Write-Host "  Failed:   " -NoNewline
Write-Host $FAILED -ForegroundColor Red
Write-Host "  Warnings: " -NoNewline
Write-Host $WARNINGS -ForegroundColor Yellow
Write-Host ""

if ($FAILED -gt 0) {
    Write-Host "Some critical tests failed!" -ForegroundColor Red
    exit 1
} else {
    Write-Host "All critical tests passed!" -ForegroundColor Green
    if ($WARNINGS -gt 0) {
        Write-Host "Note: $WARNINGS optional test(s) skipped or failed" -ForegroundColor Yellow
    }
    exit 0
}
