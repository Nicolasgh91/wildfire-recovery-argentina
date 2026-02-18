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

validate_frontend_build_env() {
    local missing_vars=()

    local supabase_url
    local supabase_anon_key
    supabase_url="$(get_env_value VITE_SUPABASE_URL "")"
    supabase_anon_key="$(get_env_value VITE_SUPABASE_ANON_KEY "")"

    if [ -z "$supabase_url" ]; then
        supabase_url="$(get_env_value SUPABASE_URL "")"
    fi
    if [ -z "$supabase_anon_key" ]; then
        supabase_anon_key="$(get_env_value SUPABASE_ANON_KEY "")"
    fi

    if [ -z "$supabase_url" ]; then
        missing_vars+=("VITE_SUPABASE_URL (or SUPABASE_URL)")
    fi
    if [ -z "$supabase_anon_key" ]; then
        missing_vars+=("VITE_SUPABASE_ANON_KEY (or SUPABASE_ANON_KEY)")
    fi

    if [ "${#missing_vars[@]}" -gt 0 ]; then
        echo "Error: faltan variables frontend build-time en .env: ${missing_vars[*]}"
        echo "Referencia: frontend/.env.production.example"
        exit 1
    fi

    local api_base_url
    api_base_url="$(get_env_value VITE_API_BASE_URL /api/v1)"
    if echo "$api_base_url" | grep -Eq 'localhost|127\.0\.0\.1'; then
        echo "Error: VITE_API_BASE_URL no debe apuntar a localhost/127.0.0.1 en produccion"
        echo "Valor actual: $api_base_url"
        exit 1
    fi
}

rebuild_frontend() {
    validate_frontend_build_env
    echo "Rebuilding frontend image..."
    docker compose -f "$COMPOSE_FILE" build --no-cache frontend
    docker compose -f "$COMPOSE_FILE" up -d frontend nginx
    echo "Frontend rebuilt and nginx refreshed"
}

case "${1:-}" in
    --build)
        BUILD_TARGET="${2:-all}"
        if [ "$BUILD_TARGET" = "frontend" ]; then
            rebuild_frontend
        elif [ "$BUILD_TARGET" = "all" ]; then
            validate_frontend_build_env
            echo "Rebuilding images..."
            docker compose -f "$COMPOSE_FILE" build --no-cache
            docker compose -f "$COMPOSE_FILE" up -d
            echo "Deploy completado con rebuild"
        else
            echo "Rebuilding service: $BUILD_TARGET"
            docker compose -f "$COMPOSE_FILE" build --no-cache "$BUILD_TARGET"
            docker compose -f "$COMPOSE_FILE" up -d "$BUILD_TARGET"
            echo "Servicio rebuilt: $BUILD_TARGET"
        fi
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
        validate_frontend_build_env
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

        validate_frontend_build_env

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
            echo "  ./scripts/deploy.sh --logs"
        fi
        ;;
esac
