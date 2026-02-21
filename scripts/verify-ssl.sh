#!/bin/bash

# ForestGuard SSL Verification Script
# Verifies SSL certificate files and HTTPS connectivity in Docker mode.

set -euo pipefail

DOMAIN="${SSL_DOMAIN:-forestguard.freedynamicdns.org}"

echo "Verifying SSL configuration for ${DOMAIN}"
echo ""

# Check if certificates exist
if [ ! -f "./certbot/conf/live/${DOMAIN}/fullchain.pem" ]; then
    echo "No certificates found. Run ./scripts/setup-ssl.sh first"
    exit 1
fi

# Check certificate files
echo "Checking certificate files..."
ls -la "./certbot/conf/live/${DOMAIN}/"

# Check certificate expiry
echo ""
echo "Certificate expiry dates:"
openssl x509 -in "./certbot/conf/live/${DOMAIN}/fullchain.pem" -noout -dates

# Check certificate subject
echo ""
echo "Certificate subject:"
openssl x509 -in "./certbot/conf/live/${DOMAIN}/fullchain.pem" -noout -subject

# Check certificate issuer
echo ""
echo "Certificate issuer:"
openssl x509 -in "./certbot/conf/live/${DOMAIN}/fullchain.pem" -noout -issuer

# Test HTTPS connection
echo ""
echo "Testing HTTPS connection..."
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "https://${DOMAIN}" 2>/dev/null || echo "000")

if [ "${HTTP_STATUS}" = "200" ]; then
    echo "HTTPS is working correctly (HTTP ${HTTP_STATUS})"
elif [ "${HTTP_STATUS}" = "000" ]; then
    echo "Failed to connect to HTTPS server"
    echo "Check if the server is running: docker compose ps"
    echo "Check nginx logs: docker compose logs nginx"
else
    echo "HTTPS returned HTTP ${HTTP_STATUS}"
fi

# Test SSL certificate chain
echo ""
echo "Testing SSL certificate chain..."
if echo | openssl s_client -connect "${DOMAIN}:443" -servername "${DOMAIN}" 2>/dev/null | grep -q "Verify return code: 0 (ok)"; then
    echo "SSL certificate chain is valid"
else
    echo "SSL certificate chain validation failed"
    echo "Running detailed SSL check..."
    echo | openssl s_client -connect "${DOMAIN}:443" -servername "${DOMAIN}" 2>/dev/null | grep "Verify return code"
fi

# Test OCSP stapling
echo ""
echo "Testing OCSP stapling..."
OCSP_RESPONSE=$(echo | openssl s_client -connect "${DOMAIN}:443" -servername "${DOMAIN}" -status 2>/dev/null | grep -A 17 "OCSP response:" || echo "No OCSP response")

if echo "${OCSP_RESPONSE}" | grep -q "OCSP Response Status: successful"; then
    echo "OCSP stapling is working"
    echo "${OCSP_RESPONSE}" | grep "Cert Status:" || true
else
    echo "OCSP stapling may not be working"
    echo "This can be normal for new certificates"
fi

# Check certificate status with Certbot
echo ""
echo "Certbot certificate status:"
docker compose --profile ssl run --rm certbot certificates || echo "Certbot command failed"

# Show next renewal date
echo ""
echo "Next renewal check:"
echo "- Use cron/systemd to call: ./scripts/renew-ssl-cron.sh"
echo "- Manual dry-run: ./scripts/renew-ssl.sh --dry-run"

echo ""
echo "SSL verification complete"
echo ""
echo "Quick commands:"
echo "- Test HTTPS: curl -I https://${DOMAIN}"
echo "- Check nginx logs: docker compose logs nginx"
echo "- Renew certificates: ./scripts/renew-ssl.sh"
