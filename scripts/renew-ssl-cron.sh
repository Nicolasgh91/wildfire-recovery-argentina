#!/bin/bash

# ForestGuard scheduled SSL renewal (Docker mode).
# Intended for cron/systemd timer usage.

set -euo pipefail

DOMAIN="${SSL_DOMAIN:-forestguard.freedynamicdns.org}"
IS_DRY_RUN=false
ARGS=()

for arg in "$@"; do
    if [ "$arg" = "--dry-run" ]; then
        IS_DRY_RUN=true
    fi
    ARGS+=("$arg")
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

echo "Running scheduled certbot renewal for ${DOMAIN}"
docker compose --profile ssl run --rm certbot renew \
    --webroot \
    --webroot-path=/var/www/certbot \
    "${ARGS[@]}"

if [ "${IS_DRY_RUN}" = true ]; then
    echo "Dry-run mode detected; skipping nginx reload."
    exit 0
fi

if docker compose exec -T nginx nginx -s reload >/dev/null 2>&1; then
    echo "Nginx reloaded after certificate renewal."
else
    echo "Nginx reload failed; restarting nginx."
    docker compose restart nginx
fi

