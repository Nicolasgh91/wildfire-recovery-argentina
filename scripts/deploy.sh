#!/bin/bash
# =============================================================================
# FORESTGUARD - Deploy Script
# =============================================================================
#
# Uso:
#   ./scripts/deploy.sh          # Deploy normal
#   ./scripts/deploy.sh --build  # Rebuild de la imagen
#   ./scripts/deploy.sh --build frontend  # Rebuild solo frontend + nginx
#   ./scripts/deploy.sh --logs   # Ver logs
#   ./scripts/deploy.sh --stop   # Detener servicios
#
# =============================================================================

set -euo pipefail

APP_DIR="/home/opc"
COMPOSE_FILE="docker-compose.yml"

cd "$APP_DIR"

get_env_value() {
    local key="$1"
    local default="$2"

    if [ -n "${!key:-}" ]; then
        echo "${!key}"
        return
    fi

    if [ -f .env ]; then
        local parsed
        parsed=$(grep -E "^${key}=" .env | tail -n 1 | cut -d'=' -f2- | tr -d '\r' || true)
        if [ -n "$parsed" ]; then
            echo "$parsed"
            return
        fi
    fi

    echo "$default"
}

nginx_is_running() {
    docker compose -f "$COMPOSE_FILE" ps --status running --services | grep -q '^nginx$'
}

case "${1:-}" in
    --build)
        echo "Rebuilding images..."
        docker compose -f "$COMPOSE_FILE" pull
        docker compose -f "$COMPOSE_FILE" up -d
        echo "Deploy completado con rebuild"
        ;;
    --logs)
        echo "Mostrando logs..."
        docker compose -f "$COMPOSE_FILE" logs -f
        ;;
    --stop)
        echo "Deteniendo servicios..."
        docker compose -f "$COMPOSE_FILE" stop
        echo "Servicios detenidos"
        ;;
    --restart)
        echo "Reiniciando servicios..."
        docker compose -f "$COMPOSE_FILE" restart
        echo "Servicios reiniciados"
        ;;
    --status)
        echo "Estado de servicios:"
        docker compose -f "$COMPOSE_FILE" ps
        ;;
    --pull)
        echo "Actualizando codigo..."
        git pull origin main
        docker compose -f "$COMPOSE_FILE" up -d --remove-orphans
        echo "Codigo actualizado y desplegado"
        ;;
    *)
        echo "Desplegando ForestGuard..."

        # Verificar que existe .env
        if [ ! -f .env ]; then
            echo "Error: Archivo .env no encontrado"
            echo "Ejecutar: cp .env.template .env && nano .env"
            exit 1
        fi

        SSL_DOMAIN="$(get_env_value SSL_DOMAIN forestguard.freedynamicdns.org)"
        CERT_DIR="./certbot/conf/live/${SSL_DOMAIN}"
        FULLCHAIN_PATH="${CERT_DIR}/fullchain.pem"
        PRIVKEY_PATH="${CERT_DIR}/privkey.pem"
        CHAIN_PATH="${CERT_DIR}/chain.pem"

        # Auto-bootstrap SSL para primer deploy
        if [ ! -f "$FULLCHAIN_PATH" ] || [ ! -f "$PRIVKEY_PATH" ] || [ ! -f "$CHAIN_PATH" ]; then
            echo "No se encontraron certificados SSL para ${SSL_DOMAIN}. Ejecutando bootstrap automatico..."
            if ! ./scripts/setup-ssl.sh; then
                echo "Fallo el bootstrap SSL. Revisar DNS/puertos 80-443 y logs:"
                echo "- docker compose -f $COMPOSE_FILE logs nginx --tail=100"
                echo "- docker compose -f $COMPOSE_FILE --profile ssl run --rm certbot certificates"
                exit 1
            fi
        else
            echo "Certificados SSL encontrados en ${CERT_DIR}"
        fi

        echo "=== Phase 0: Pull images (before stopping anything) ==="
        docker compose -f "$COMPOSE_FILE" pull --quiet

        echo "=== Phase 1: Stop workers gracefully ==="
        docker compose -f "$COMPOSE_FILE" stop worker-gee worker-fast celery-beat 2>/dev/null || true
        sleep 5

        echo "=== Phase 2: Restart infrastructure ==="
        docker compose -f "$COMPOSE_FILE" up -d redis
        echo "Waiting for Redis..."
        timeout 30 bash -c "until docker compose -f $COMPOSE_FILE exec -T redis redis-cli ping 2>/dev/null | grep -q PONG; do sleep 2; done"

        echo "=== Phase 3: Start API ==="
        docker compose -f "$COMPOSE_FILE" up -d api
        echo "Waiting for API health..."
        timeout 120 bash -c "until curl -sf http://localhost:8000/health >/dev/null 2>&1; do sleep 5; done"

        echo "=== Phase 4: Start frontend + nginx ==="
        docker compose -f "$COMPOSE_FILE" up -d frontend nginx
        sleep 5

        echo "=== Phase 5: Start workers (staggered) ==="
        docker compose -f "$COMPOSE_FILE" up -d worker-fast
        sleep 10
        docker compose -f "$COMPOSE_FILE" up -d worker-gee
        sleep 10
        docker compose -f "$COMPOSE_FILE" up -d celery-beat

        echo "=== Phase 6: Cleanup ==="
        docker image prune -f --filter "until=24h" 2>/dev/null || true
        docker builder prune -f --keep-storage=500MB 2>/dev/null || true

        echo "=== Phase 7: Verify ==="
        docker compose -f "$COMPOSE_FILE" ps --format "table {{.Name}}\t{{.Status}}"

        echo "=== Deploy complete ==="
        ;;
esac
