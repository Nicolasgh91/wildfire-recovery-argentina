#!/bin/bash
# =============================================================================
# FORESTGUARD SMOKE TESTS
# =============================================================================
#
# Quick validation script to verify critical API functionality.
# Run after deployment to ensure basic operations work correctly.
#
# Usage:
#   ./scripts/smoke_test.sh [BASE_URL] [API_KEY]
#
# Example:
#   ./scripts/smoke_test.sh https://api.forestguard.ar sk_live_xxx
#
# Exit codes:
#   0 - All tests passed
#   1 - One or more tests failed
#
# Author: ForestGuard Team
# Version: 1.0.0
# Last Updated: 2026-02-08
# =============================================================================

set -e

# Configuration
BASE_URL="${1:-http://localhost:8000}"
API_KEY="${2:-}"
TIMEOUT=10
PASSED=0
FAILED=0

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================"
echo "  ForestGuard Smoke Tests"
echo "  Base URL: $BASE_URL"
echo "========================================"
echo ""

# Helper function to run a test
run_test() {
    local name="$1"
    local method="$2"
    local endpoint="$3"
    local expected_status="$4"
    local extra_args="${5:-}"
    
    printf "%-40s" "Testing: $name..."
    
    # Build curl command
    local url="${BASE_URL}${endpoint}"
    local status
    
    if [ "$method" = "GET" ]; then
        status=$(curl -s -o /dev/null -w "%{http_code}" --max-time $TIMEOUT $extra_args "$url")
    else
        status=$(curl -s -o /dev/null -w "%{http_code}" --max-time $TIMEOUT -X "$method" $extra_args "$url")
    fi
    
    if [ "$status" = "$expected_status" ]; then
        echo -e "${GREEN}PASSED${NC} (HTTP $status)"
        ((PASSED++))
        return 0
    else
        echo -e "${RED}FAILED${NC} (expected $expected_status, got $status)"
        ((FAILED++))
        return 1
    fi
}

# Helper for authenticated tests
run_auth_test() {
    local name="$1"
    local method="$2"
    local endpoint="$3"
    local expected_status="$4"
    
    if [ -z "$API_KEY" ]; then
        echo -e "${YELLOW}SKIPPED${NC} (no API key)"
        return 0
    fi
    
    run_test "$name" "$method" "$endpoint" "$expected_status" "-H 'X-API-Key: $API_KEY'"
}

echo "=== Health Checks ==="
run_test "Liveness probe" "GET" "/health" "200"
run_test "API v1 health detailed" "GET" "/api/v1/health/live" "200"
run_test "API v1 health ready" "GET" "/api/v1/health/ready" "200"
echo ""

echo "=== Public Endpoints ==="
run_test "List fires (public)" "GET" "/api/v1/fires/" "200"
run_test "Fire statistics" "GET" "/api/v1/fires/stats" "200"
run_test "Active fires for home" "GET" "/api/v1/fires/home" "200"
echo ""

echo "=== Validation Tests (SEC-001, SEC-003) ==="
run_test "Page size limit (101)" "GET" "/api/v1/payments/credits/transactions?page_size=101" "422"
run_test "Page zero rejected" "GET" "/api/v1/payments/credits/transactions?page=0" "422"
run_test "Max records limit (10001)" "GET" "/api/v1/fires/export?max_records=10001" "422"
echo ""

echo "=== Authentication Tests ==="
run_test "Auth required (no key)" "GET" "/api/v1/audit/land-use" "401"
run_test "Payments require auth" "GET" "/api/v1/payments/credits/balance" "401"
echo ""

echo "=== CORS Check (SEC-002) ==="
# CORS should not return * for allowed origins
CORS_RESPONSE=$(curl -s -H "Origin: http://evil.com" -I "${BASE_URL}/health" 2>/dev/null | grep -i "access-control-allow-origin" || true)
if echo "$CORS_RESPONSE" | grep -q "\*"; then
    echo -e "CORS wildcard check..........................${RED}FAILED${NC} (found *)"
    ((FAILED++))
else
    echo -e "CORS wildcard check..........................${GREEN}PASSED${NC}"
    ((PASSED++))
fi
echo ""

echo "=== Response Headers ==="
# Check for X-Request-ID header (ROB-002)
HEADERS=$(curl -s -I "${BASE_URL}/health" 2>/dev/null)
if echo "$HEADERS" | grep -qi "x-request-id"; then
    echo -e "X-Request-ID header present..................${GREEN}PASSED${NC}"
    ((PASSED++))
else
    echo -e "X-Request-ID header present..................${RED}FAILED${NC}"
    ((FAILED++))
fi

# Check for X-Process-Time header
if echo "$HEADERS" | grep -qi "x-process-time"; then
    echo -e "X-Process-Time header present................${GREEN}PASSED${NC}"
    ((PASSED++))
else
    echo -e "X-Process-Time header present................${RED}FAILED${NC}"
    ((FAILED++))
fi
echo ""

echo "=== Authenticated Tests ==="
if [ -n "$API_KEY" ]; then
    run_auth_test "Land audit endpoint" "POST" "/api/v1/audit/land-use" "422"
else
    echo -e "${YELLOW}Skipped authenticated tests (no API_KEY provided)${NC}"
fi
echo ""

# Summary
echo "========================================"
echo "  RESULTS"
echo "========================================"
echo -e "  Passed: ${GREEN}$PASSED${NC}"
echo -e "  Failed: ${RED}$FAILED${NC}"
echo ""

if [ $FAILED -gt 0 ]; then
    echo -e "${RED}Some tests failed!${NC}"
    exit 1
else
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
fi
