#!/bin/bash

# ForestGuard SSL Certificate Renewal Script
# Manual or scheduled certificate renewal with nginx reload.

set -euo pipefail

DOMAIN="${SSL_DOMAIN:-forestguard.freedynamicdns.org}"
EXTRA_ARGS=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --force-renewal|--force)
            EXTRA_ARGS+=("--force-renewal")
            ;;
        --dry-run)
            EXTRA_ARGS+=("--dry-run")
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: ./scripts/renew-ssl.sh [--dry-run] [--force-renewal]"
            exit 1
            ;;
    esac
    shift
done

echo "Renewing SSL certificates for ${DOMAIN}"

# Check if certificates exist
if [ ! -f "./certbot/conf/live/${DOMAIN}/fullchain.pem" ]; then
    echo "No certificates found. Run ./scripts/setup-ssl.sh first"
    exit 1
fi

# Show current certificate expiry
echo "Current certificate expiry:"
openssl x509 -in "./certbot/conf/live/${DOMAIN}/fullchain.pem" -noout -dates

# Renew certificates
echo "Running certificate renewal..."
docker compose --profile ssl run --rm certbot renew \
    --webroot \
    --webroot-path=/var/www/certbot \
    "${EXTRA_ARGS[@]}"

# Check if renewal was successful
if [ ! -f "./certbot/conf/live/${DOMAIN}/fullchain.pem" ]; then
    echo "Certificate renewal failed"
    exit 1
fi

echo "Certificate renewal command finished successfully"

# Reload nginx to apply certificates
if docker compose exec -T nginx nginx -s reload >/dev/null 2>&1; then
    echo "Nginx reloaded successfully"
else
    echo "Nginx reload via signal failed; restarting nginx"
    docker compose restart nginx
fi

# Show certificate expiry after renewal
echo "Certificate expiry after renewal:"
openssl x509 -in "./certbot/conf/live/${DOMAIN}/fullchain.pem" -noout -dates

# Check certificate details
echo "Updated certificate details:"
openssl x509 -in "./certbot/conf/live/${DOMAIN}/fullchain.pem" -noout -subject
openssl x509 -in "./certbot/conf/live/${DOMAIN}/fullchain.pem" -noout -issuer

echo ""
echo "Certificate status:"
docker compose --profile ssl run --rm certbot certificates

echo ""
echo "Quick checks:"
echo "- HTTPS test: curl -I https://${DOMAIN}"
echo "- Nginx logs: docker compose logs nginx"
