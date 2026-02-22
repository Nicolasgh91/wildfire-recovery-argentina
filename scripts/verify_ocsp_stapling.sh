#!/bin/bash
#
# Verify OCSP Stapling Configuration
# 
# This script tests whether OCSP stapling is working correctly on the server.
# Run this after deploying the updated nginx.conf.
#

set -e

DOMAIN="forestguard.freedynamicdns.org"
PORT="443"

echo "=========================================="
echo "OCSP Stapling Verification"
echo "=========================================="
echo ""
echo "Domain: $DOMAIN"
echo "Port: $PORT"
echo ""

# Test 1: Check if OCSP stapling is enabled
echo "Test 1: Checking OCSP Stapling Status..."
echo "----------------------------------------"

OCSP_RESPONSE=$(echo | openssl s_client -connect "$DOMAIN:$PORT" -servername "$DOMAIN" -status 2>/dev/null | grep -A 17 "OCSP response:")

if echo "$OCSP_RESPONSE" | grep -q "OCSP Response Status: successful"; then
    echo "✅ OCSP Stapling is ENABLED and working"
    echo ""
    echo "Response Details:"
    echo "$OCSP_RESPONSE"
else
    echo "❌ OCSP Stapling is NOT working"
    echo ""
    echo "Response:"
    echo "$OCSP_RESPONSE"
    exit 1
fi

echo ""
echo "=========================================="

# Test 2: Verify certificate status
echo "Test 2: Verifying Certificate Status..."
echo "----------------------------------------"

if echo "$OCSP_RESPONSE" | grep -q "Cert Status: good"; then
    echo "✅ Certificate status: GOOD"
else
    echo "⚠️  Certificate status: NOT GOOD"
    echo "$OCSP_RESPONSE" | grep "Cert Status"
fi

echo ""
echo "=========================================="

# Test 3: Check response age
echo "Test 3: Checking OCSP Response Freshness..."
echo "----------------------------------------"

PRODUCED_AT=$(echo "$OCSP_RESPONSE" | grep "Produced At:" | head -1)
THIS_UPDATE=$(echo "$OCSP_RESPONSE" | grep "This Update:" | head -1)
NEXT_UPDATE=$(echo "$OCSP_RESPONSE" | grep "Next Update:" | head -1)

echo "$PRODUCED_AT"
echo "$THIS_UPDATE"
echo "$NEXT_UPDATE"

echo ""
echo "=========================================="
echo "✅ OCSP Stapling verification complete!"
echo "=========================================="
