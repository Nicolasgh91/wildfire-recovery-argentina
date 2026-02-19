#!/bin/bash

# Vestigia SSL Certificate Setup Script
# This script generates initial SSL certificates using Certbot (Docker mode) for Vestigia.

set -euo pipefail

DOMAIN="${SSL_DOMAIN:-forestguard.freedynamicdns.org}"
EMAIL="${SSL_EMAIL:-admin@forestguard.freedynamicdns.org}"
TEMP_NGINX_CONF="nginx-temp.runtime.conf"

echo "Setting up SSL certificates for ${DOMAIN}"

# Check if certificates already exist
if [ -f "./certbot/conf/live/${DOMAIN}/fullchain.pem" ]; then
    echo "Certificates already exist. Checking expiry..."
    openssl x509 -in "./certbot/conf/live/${DOMAIN}/fullchain.pem" -noout -dates
    echo "To renew certificates, run: ./scripts/renew-ssl.sh"
    exit 0
fi

# Create temporary nginx config for certificate generation
echo "Creating temporary nginx config for Let's Encrypt validation..."
cat > "${TEMP_NGINX_CONF}" << EOF
events {
    worker_connections 1024;
}

http {
    server {
        listen 80;
        server_name ${DOMAIN};

        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }

        location / {
            return 301 https://\$server_name\$request_uri;
        }
    }
}
EOF

# Backup original nginx config and use temporary one
echo "Setting up temporary nginx configuration..."
cp nginx.conf nginx.conf.backup
cp "${TEMP_NGINX_CONF}" nginx.conf

# Start nginx with temporary config
echo "Starting nginx for certificate validation..."
docker compose up -d nginx

# Wait for nginx to be ready
echo "Waiting for nginx to start..."
sleep 10

# Generate certificates
echo "Generating SSL certificates..."
docker compose --profile ssl run --rm certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    --email "${EMAIL}" \
    --agree-tos \
    --no-eff-email \
    -d "${DOMAIN}"

# Check if certificates were generated
if [ ! -f "./certbot/conf/live/${DOMAIN}/fullchain.pem" ]; then
    echo "Certificate generation failed."
    echo "Restoring original nginx config..."
    cp nginx.conf.backup nginx.conf
    docker compose up -d nginx
    exit 1
fi

echo "Certificates generated successfully."

# Restore original nginx configuration
echo "Restoring production nginx configuration..."
cp nginx.conf.backup nginx.conf
rm -f "${TEMP_NGINX_CONF}" nginx.conf.backup

# Restart nginx with production config
echo "Restarting nginx with SSL configuration..."
docker compose up -d nginx

# Verify SSL setup
echo "Verifying SSL configuration..."
sleep 15

# Test SSL certificate
echo "Certificate details:"
openssl x509 -in "./certbot/conf/live/${DOMAIN}/fullchain.pem" -noout -dates
openssl x509 -in "./certbot/conf/live/${DOMAIN}/fullchain.pem" -noout -subject

# Test HTTPS connection
echo "Testing HTTPS connection..."
if curl -s -o /dev/null -w "%{http_code}" "https://${DOMAIN}" | grep -q "200"; then
    echo "HTTPS is working correctly."
else
    echo "HTTPS test failed. Check nginx logs: docker compose logs nginx"
fi

echo ""
echo "SSL setup complete."
echo ""
echo "Next steps:"
echo "1. Update your DNS to point ${DOMAIN} to this server"
echo "2. Verify HTTPS works in browser: https://${DOMAIN}"
echo "3. Configure renewal scheduler (cron/systemd) using ./scripts/renew-ssl-cron.sh"
echo "4. Check SSL Labs score: https://www.ssllabs.com/ssltest/"
echo ""
echo "To check renewal status: docker compose --profile ssl run --rm certbot certificates"
