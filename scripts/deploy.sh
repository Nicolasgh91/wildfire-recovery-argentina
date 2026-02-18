#!/bin/bash
# =============================================================================
# FORESTGUARD - Deploy Script
# =============================================================================
#
# Uso:
#   ./deploy.sh          # Deploy normal
#   ./deploy.sh --build  # Rebuild de la imagen
#   ./deploy.sh --logs   # Ver logs
#   ./deploy.sh --stop   # Detener servicios
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
        docker compose -f "$COMPOSE_FILE" build --no-cache
        docker compose -f "$COMPOSE_FILE" up -d
        echo "Deploy completado con rebuild"
        ;;
    --logs)
        echo "Mostrando logs..."
        docker compose -f "$COMPOSE_FILE" logs -f
        ;;
    --stop)
        echo "Deteniendo servicios..."
        docker compose -f "$COMPOSE_FILE" down
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
        docker compose -f "$COMPOSE_FILE" up -d --build
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

        # Pull de imagenes base
        docker compose -f "$COMPOSE_FILE" --profile ssl pull nginx certbot 2>/dev/null || true

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

        # Levantar servicios
        docker compose -f "$COMPOSE_FILE" up -d

        # Esperar a que nginx inicie
        echo "Waiting for Nginx to start..."
        sleep 10

        # Validacion segura de nginx
        echo "Testing Nginx configuration..."
        if ! nginx_is_running; then
            echo "Nginx container is not running. Showing logs..."
            docker compose -f "$COMPOSE_FILE" logs nginx --tail=100 || true
            exit 1
        fi

        if ! docker compose -f "$COMPOSE_FILE" exec -T nginx nginx -t; then
            echo "Nginx configuration has errors"
            docker compose -f "$COMPOSE_FILE" logs nginx --tail=100 || true
            exit 1
        fi

        # Esperar a que la API este lista
        echo "Esperando a que la API inicie..."
        sleep 10

        # Health check
        if curl -s http://localhost/health > /dev/null; then
            echo "Deploy completado exitosamente"
            echo ""
            echo "Estado:"
            docker compose -f "$COMPOSE_FILE" ps
            echo ""
            echo "URLs:"
            echo "  - Health: http://$(curl -s ifconfig.me)/health"
            echo "  - Docs:   http://$(curl -s ifconfig.me)/docs"
            echo "  - API:    http://$(curl -s ifconfig.me)/api/v1/"
        else
            echo "La API puede estar iniciando aun. Verificar con:"
            echo "  ./deploy.sh --logs"
        fi
        ;;
esac
