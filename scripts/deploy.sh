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

        # Pull de imagenes de GHCR
        echo "=== Pulling images ==="
        if ! docker compose -f "$COMPOSE_FILE" pull; then
            echo "ERROR: Failed to pull images from GHCR."
            echo "  Check that the backend-build workflow completed successfully."
            exit 1
        fi

        # Cleanup before building new images
        echo "=== Pre-build cleanup ==="
        docker container prune -f
        docker image prune -f
        docker builder prune -af

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

        # Levantar servicios core primero (Redis, API, Frontend, Nginx)
        echo "=== Iniciando servicios core ==="
        docker compose -f "$COMPOSE_FILE" up -d --remove-orphans redis api frontend nginx

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

        # Fase A: Backend Readiness (API directa)
        echo "=== Fase A: Backend Readiness ==="
        API_READY=false
        for i in $(seq 1 12); do
            if curl -fsS --max-time 5 http://localhost:8000/health >/dev/null 2>&1; then
                echo "Backend listo en el intento $i"
                API_READY=true
                break
            fi
            echo "  Backend intento $i/12 falló, reintentando en 5s..."
            sleep 5
        done

        if ! $API_READY; then
            echo "ERROR: Backend (API) falló en iniciar tras 12 intentos."
            echo "=== Diagnostic Logs: API ==="
            docker compose -f "$COMPOSE_FILE" logs --tail=100 api || true
            echo "=== Diagnostic Logs: Contenedores ==="
            docker compose -f "$COMPOSE_FILE" ps -a || true
            exit 1
        fi

        # Fase B: Edge Readiness (Nginx Proxy)
        echo "=== Fase B: Edge Readiness ==="
        EDGE_READY=false
        for i in $(seq 1 6); do
            if curl -fsS -L --max-time 5 http://localhost/health >/dev/null 2>&1; then
                echo "Edge (HTTP) listo en el intento $i"
                EDGE_READY=true
                break
            fi
            if curl -fsS --insecure --max-time 5 https://localhost/health >/dev/null 2>&1; then
                echo "Edge (HTTPS) listo en el intento $i"
                EDGE_READY=true
                break
            fi
            echo "  Edge intento $i/6 falló, reintentando en 5s..."
            sleep 5
        done
        
        if $EDGE_READY; then
            # Fase C: Iniciar Workers (ligueros + pesados)
            echo "=== Fase C: Iniciando Workers ==="
            docker compose -f "$COMPOSE_FILE" --profile workers-heavy up -d \
                worker-ingestion \
                worker-clustering \
                worker-analysis \
                worker-vae \
                worker-reports \
                celery-beat \
                flower || true

            echo "Deploy completado exitosamente"
            echo ""
            echo "Estado final:"
            docker compose -f "$COMPOSE_FILE" --profile workers-heavy ps
            echo ""
            echo "URLs:"
            echo "  - Health: http://$(curl -s ifconfig.me)/health"
            echo "  - Docs:   http://$(curl -s ifconfig.me)/docs"
            echo "  - API:    http://$(curl -s ifconfig.me)/api/v1/"
            echo "  - Flower: http://$(curl -s ifconfig.me):5555"
        else
            echo "ERROR: Edge (Nginx) health check falló tras 6 intentos."
            echo "=== Diagnostic Logs: Nginx ==="
            docker compose -f "$COMPOSE_FILE" logs --tail=100 nginx || true
            echo "=== Diagnostic Logs: Nginx Config ==="
            docker compose -f "$COMPOSE_FILE" exec -T nginx nginx -t || true
            echo "=== Diagnostic Logs: Contenedores ==="
            docker compose -f "$COMPOSE_FILE" ps -a || true
            exit 1
        fi
        ;;
esac
