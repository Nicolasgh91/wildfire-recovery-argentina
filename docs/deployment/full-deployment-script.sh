#!/bin/bash

# Full Deployment Script - Start All Services & Deploy CI-Built Frontend
# Usage: ./full-deployment-script.sh

set -e  # Exit on any error

echo "🚀 Starting Full ForestGuard Deployment..."
echo "================================================"

# Phase 1: Environment Preparation
echo "📋 Phase 1: Environment Preparation"

# Check Docker and docker-compose
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose is not installed"
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ .env file not found. Please create it with required environment variables."
    exit 1
fi

# Check GCloud credentials
if [ ! -d ~/.config/gcloud ]; then
    echo "❌ Google Cloud credentials not found at ~/.config/gcloud"
    exit 1
fi

echo "✅ Environment checks passed"

# Phase 2: Start Backend Services
echo ""
echo "🏗️  Phase 2: Starting Backend Services"

# Stop any existing services
echo "🔄 Stopping any existing services..."
docker compose down --remove-orphans 2>/dev/null || true

# Start Redis first
echo "📦 Starting Redis..."
docker compose up -d redis

# Wait for Redis to be healthy
echo "⏳ Waiting for Redis to be healthy..."
for i in {1..30}; do
    if docker compose exec -T redis redis-cli ping > /dev/null 2>&1; then
        echo "✅ Redis is healthy"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ Redis failed to become healthy"
        docker compose logs redis
        exit 1
    fi
    sleep 2
done

# Start API
echo "🔧 Starting API..."
docker compose up -d api

# Wait for API to be healthy
echo "⏳ Waiting for API to be healthy..."
for i in {1..60}; do
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        echo "✅ API is healthy"
        break
    fi
    if [ $i -eq 60 ]; then
        echo "❌ API failed to become healthy"
        docker compose logs api
        exit 1
    fi
    sleep 2
done

# Start Worker Services
echo "👷 Starting Worker Services..."
docker compose up -d worker-ingestion worker-clustering worker-analysis

# Start Celery Beat
echo "⏰ Starting Celery Beat..."
docker compose up -d celery-beat

# Start Flower Monitoring
echo "🌸 Starting Flower Monitoring..."
docker compose up -d flower

echo "✅ All backend services started"

# Phase 3: Deploy Frontend from GHCR
echo ""
echo "🎯 Phase 3: Deploying Frontend from GHCR"

# Disable override file
if [ -f docker-compose.override.yml ]; then
    echo "🔄 Disabling docker-compose.override.yml..."
    mv docker-compose.override.yml docker-compose.override.yml.backup
fi

# Update docker-compose.yml to use GHCR image
echo "🔄 Updating docker-compose.yml for GHCR image..."
# Create backup
cp docker-compose.yml docker-compose.yml.backup

# Comment out build section and add image
sed -i 's/^    build:/    # build:/' docker-compose.yml
sed -i '/^    context: \/frontend$/,/^    dockerfile: Dockerfile$/s/^/    # /' docker-compose.yml

# Add image reference if not present
if ! grep -q "ghcr.io/nicolasgh91/wildfire-recovery-argentina/frontend:latest" docker-compose.yml; then
    sed -i '/^    # dockerfile: Dockerfile$/a\    image: ghcr.io/nicolasgh91/wildfire-recovery-argentina/frontend:latest' docker-compose.yml
fi

# Pull the CI-built frontend image
echo "📥 Pulling CI-built frontend image..."
docker pull ghcr.io/nicolasgh91/wildfire-recovery-argentina/frontend:latest

# Start frontend
echo "🚀 Starting Frontend..."
docker compose up -d frontend

# Wait for frontend to be ready
echo "⏳ Waiting for Frontend to be ready..."
sleep 10

# Check frontend container
if ! docker compose ps frontend | grep -q "Up"; then
    echo "❌ Frontend container failed to start"
    docker compose logs frontend
    exit 1
fi

echo "✅ Frontend deployed successfully"

# Start Nginx Reverse Proxy
echo "🌐 Starting Nginx Reverse Proxy..."
docker compose up -d nginx

# Verify nginx configuration
echo "🔍 Verifying Nginx configuration..."
if ! docker compose exec -T nginx nginx -t > /dev/null 2>&1; then
    echo "❌ Nginx configuration is invalid"
    docker compose exec nginx nginx -t
    exit 1
fi

echo "✅ Nginx started successfully"

# Phase 4: Full System Verification
echo ""
echo "🔍 Phase 4: Full System Verification"

echo "📊 Service Status:"
docker compose ps

echo ""
echo "🧪 Health Checks:"

# Test API
echo "🔧 Testing API health..."
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ API health check passed"
else
    echo "❌ API health check failed"
fi

# Test Frontend through Nginx
echo "🎨 Testing Frontend through Nginx..."
if curl -s -o /dev/null -w "%{http_code}" http://localhost/ | grep -q "200"; then
    echo "✅ Frontend accessible through Nginx"
else
    echo "❌ Frontend not accessible through Nginx"
fi

# Test Flower
echo "🌸 Testing Flower monitoring..."
if curl -s -o /dev/null -w "%{http_code}" http://localhost:5555/ | grep -q "200"; then
    echo "✅ Flower monitoring accessible"
else
    echo "❌ Flower monitoring not accessible"
fi

# Test Redis connectivity
echo "📦 Testing Redis connectivity..."
if docker compose exec -T redis redis-cli ping > /dev/null 2>&1; then
    echo "✅ Redis connectivity OK"
else
    echo "❌ Redis connectivity failed"
fi

# Test API-Frontend connectivity
echo "🔗 Testing API-Frontend connectivity..."
if docker compose exec -T frontend curl -f http://api:8000/health > /dev/null 2>&1; then
    echo "✅ Frontend can reach API"
else
    echo "❌ Frontend cannot reach API"
fi

# Resource Monitoring
echo ""
echo "📈 Resource Usage:"
docker stats --no-stream

echo ""
echo "🎉 Deployment Complete!"
echo "========================"
echo "📱 Frontend: http://localhost"
echo "🔧 API: http://localhost:8000"
echo "🌸 Flower (Monitoring): http://localhost:5555"
echo ""
echo "💡 To check logs: docker compose logs [service-name]"
echo "💡 To stop all: docker compose down"
echo "💡 To restart service: docker compose restart [service-name]"

# Final verification
echo ""
echo "🔍 Final Verification:"
echo "Frontend image source:"
docker images forestguard-frontend --format "table {{.Repository}}:{{.Tag}}\t{{.Size}}"

echo ""
echo "Frontend memory usage (should be < 64MB):"
docker stats forestguard-frontend --no-stream --format "table {{.Name}}\t{{.MemUsage}}"

echo ""
echo "✅ All services deployed successfully!"
