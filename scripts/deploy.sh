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

set -e

APP_DIR="/home/opc"
COMPOSE_FILE="docker-compose.yml"

cd $APP_DIR

case "$1" in
    --build)
        echo "🔨 Rebuilding images..."
        docker-compose -f $COMPOSE_FILE build --no-cache
        docker-compose -f $COMPOSE_FILE up -d
        echo "✅ Deploy completado con rebuild"
        ;;
    --logs)
        echo "📋 Mostrando logs..."
        docker-compose -f $COMPOSE_FILE logs -f
        ;;
    --stop)
        echo "🛑 Deteniendo servicios..."
        docker-compose -f $COMPOSE_FILE down
        echo "✅ Servicios detenidos"
        ;;
    --restart)
        echo "🔄 Reiniciando servicios..."
        docker-compose -f $COMPOSE_FILE restart
        echo "✅ Servicios reiniciados"
        ;;
    --status)
        echo "📊 Estado de servicios:"
        docker-compose -f $COMPOSE_FILE ps
        ;;
    --pull)
        echo "📥 Actualizando código..."
        git pull origin main
        docker-compose -f $COMPOSE_FILE up -d --build
        echo "✅ Código actualizado y desplegado"
        ;;
    *)
        echo "🚀 Desplegando ForestGuard..."
        
        # Verificar que existe .env
        if [ ! -f .env ]; then
            echo "❌ Error: Archivo .env no encontrado"
            echo "   Ejecutar: cp .env.template .env && nano .env"
            exit 1
        fi
        
        # Pull de imágenes base
        docker-compose -f $COMPOSE_FILE pull nginx certbot 2>/dev/null || true
        
        # Levantar servicios
        docker-compose -f $COMPOSE_FILE up -d
        
        # Esperar a que la API esté lista
        echo "⏳ Esperando a que la API inicie..."
        sleep 10
        
        # Health check
        if curl -s http://localhost/health > /dev/null; then
            echo "✅ Deploy completado exitosamente"
            echo ""
            echo "📊 Estado:"
            docker-compose -f $COMPOSE_FILE ps
            echo ""
            echo "🔗 URLs:"
            echo "   - Health: http://$(curl -s ifconfig.me)/health"
            echo "   - Docs:   http://$(curl -s ifconfig.me)/docs"
            echo "   - API:    http://$(curl -s ifconfig.me)/api/v1/"
        else
            echo "⚠️ La API puede estar iniciando aún. Verificar con:"
            echo "   ./deploy.sh --logs"
        fi
        ;;
esac
