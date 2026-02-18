#!/bin/bash

# Apply Critical Fixes Script
# Run this on the VM to apply all the fixes

set -e

echo "🔧 Applying Critical Fixes to ForestGuard"
echo "======================================"

echo "📋 Fixes being applied:"
echo "1. API Dockerfile: Fix main.py import path (app.main:app)"
echo "2. Nginx config: Proxy to frontend container instead of serving local files"
echo "3. Rebuild and restart affected services"
echo ""

# Step 1: Rebuild API container with fixed Dockerfile
echo "🔧 Step 1: Rebuilding API container..."
echo "--------------------------------------"

echo "🔄 Stopping API container..."
docker compose stop api

echo "🔄 Rebuilding API container..."
docker compose build --no-cache api

echo "▶️  Starting API container..."
docker compose up -d api

echo "⏳ Waiting for API to start..."
sleep 15

echo "🧪 Testing API health..."
if curl -s -f http://localhost:8000/health >/dev/null 2>&1; then
    echo "✅ API is now responding!"
    echo "📋 API health response:"
    curl -s http://localhost:8000/health | head -3
else
    echo "❌ API still not responding"
    echo "📋 API logs:"
    docker compose logs api --tail=10
fi

echo ""

# Step 2: Restart nginx with new configuration
echo "🌐 Step 2: Restarting Nginx with new config..."
echo "-----------------------------------------------"

echo "🔄 Stopping Nginx container..."
docker compose stop nginx

echo "▶️  Starting Nginx container..."
docker compose up -d nginx

echo "⏳ Waiting for Nginx to start..."
sleep 10

echo "🧪 Testing Nginx configuration..."
if docker compose exec nginx nginx -t >/dev/null 2>&1; then
    echo "✅ Nginx configuration is valid"
else
    echo "❌ Nginx configuration has errors"
    echo "📋 Nginx config test:"
    docker compose exec nginx nginx -t
fi

echo ""

# Step 3: Test frontend connectivity
echo "🎨 Step 3: Testing Frontend connectivity..."
echo "------------------------------------------"

echo "🧪 Testing frontend container directly..."
if docker compose exec frontend curl -I http://localhost/ >/dev/null 2>&1; then
    echo "✅ Frontend container is responding internally"
else
    echo "❌ Frontend container not responding internally"
    echo "📋 Frontend logs:"
    docker compose logs frontend --tail=10
fi

echo ""

# Step 4: Test overall connectivity
echo "🔗 Step 4: Testing overall connectivity..."
echo "----------------------------------------"

echo "🧪 Testing localhost access..."
if curl -s -f http://localhost/ >/dev/null 2>&1; then
    echo "✅ Website accessible on localhost"
    echo "📋 HTTP response:"
    curl -s -I http://localhost/ | head -3
else
    echo "❌ Website not accessible on localhost"
fi

echo "🧪 Testing API from localhost..."
if curl -s -f http://localhost:8000/health >/dev/null 2>&1; then
    echo "✅ API accessible on localhost"
else
    echo "❌ API not accessible on localhost"
fi

echo ""

# Step 5: Check all services status
echo "📊 Step 5: Final service status..."
echo "---------------------------------"

echo "📋 All containers status:"
docker compose ps

echo ""
echo "📋 Resource usage:"
docker stats --no-stream

echo ""

# Step 6: Test external access
echo "🌍 Step 6: Testing external access..."
echo "------------------------------------"

echo "🧪 Testing external website access..."
if timeout 10 curl -s -I https://forestguard.freedynamicdns.org/ >/dev/null 2>&1; then
    echo "✅ Website accessible externally!"
    echo "🎉 ForestGuard is back online!"
else
    echo "❌ Website not accessible externally"
    echo "📋 This might be due to:"
    echo "   - Firewall rules in Oracle Cloud"
    echo "   - SSL certificate issues"
    echo "   - DNS propagation"
    echo ""
    echo "🔧 To check external HTTP (non-HTTPS):"
    echo "curl -I http://141.148.54.223/"
fi

echo ""

# Summary
echo "📊 Summary"
echo "=========="

echo "✅ Fixes applied:"
echo "   - API Dockerfile fixed (app.main:app)"
echo "   - Nginx configured to proxy to frontend"
echo "   - Services rebuilt and restarted"

echo ""
echo "🎯 Next steps if still down:"
echo "1. Check Oracle Cloud security list (ports 80/443)"
echo "2. Configure SSL certificates if needed"
echo "3. Check DNS resolution for forestguard.freedynamicdns.org"

echo ""
echo "📱 Access URLs:"
echo "   - Local: http://localhost/"
echo "   - API: http://localhost:8000/health"
echo "   - External: https://forestguard.freedynamicdns.org/"

echo ""
echo "✅ Fix deployment complete!"
