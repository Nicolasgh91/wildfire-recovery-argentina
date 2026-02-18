#!/bin/bash

# Critical Fixes Script - Based on VM Analysis Results
# Run this on the VM after the analysis script

set -e

echo "🔧 Applying Critical Fixes"
echo "========================"

echo "🚨 Issues Found:"
echo "1. Nginx can't resolve 'api:8000' hostname"
echo "2. API can't import 'main' module"
echo "3. Frontend not accessible directly"
echo "4. SSL certificates missing"
echo ""

# Fix 1: Diagnose and Fix API Container
echo "🔧 Fix 1: API Container Diagnosis"
echo "--------------------------------"

echo "📋 Checking API container filesystem..."
docker compose exec api ls -la /app/ 2>/dev/null || echo "❌ Cannot access API container"

echo "📋 Looking for main.py..."
docker compose exec api find /app -name "main.py" 2>/dev/null || echo "❌ main.py not found"

echo "📋 Testing Python import..."
docker compose exec api python -c "import main; print('✅ Main module imported successfully')" 2>/dev/null || echo "❌ Main module import failed"

echo "📋 Checking Python path..."
docker compose exec api python -c "import sys; print('Python path:', sys.path)" 2>/dev/null || echo "❌ Cannot check Python path"

echo ""
echo "🔄 Restarting API container..."
docker compose restart api

echo "⏳ Waiting for API to start..."
sleep 10

echo "📋 Testing API health after restart..."
if curl -s -f http://localhost:8000/health >/dev/null 2>&1; then
    echo "✅ API is now responding!"
else
    echo "❌ API still not responding"
    echo "📋 API logs after restart:"
    docker compose logs api --tail=10
fi

echo ""

# Fix 2: Fix Nginx Configuration
echo "🌐 Fix 2: Nginx Configuration"
echo "-----------------------------"

echo "📋 Testing nginx configuration..."
docker compose exec nginx nginx -t 2>/dev/null || echo "❌ Nginx configuration has errors"

echo "📋 Checking if nginx can resolve API hostname..."
docker compose exec nginx nslookup api 2>/dev/null || echo "❌ Cannot resolve API hostname"

echo "📋 Testing connectivity from nginx to API..."
docker compose exec nginx wget -qO- http://api:8000/health 2>/dev/null || echo "❌ Nginx cannot reach API"

echo "📋 Checking nginx.conf upstream configuration..."
docker compose exec nginx cat /etc/nginx/nginx.conf | grep -A 5 -B 5 "upstream" 2>/dev/null || echo "❌ Cannot read nginx.conf"

echo ""
echo "🔄 Restarting nginx container..."
docker compose restart nginx

echo "⏳ Waiting for nginx to start..."
sleep 5

echo "📋 Checking nginx logs after restart..."
docker compose logs nginx --tail=10

echo ""

# Fix 3: Test Frontend Container
echo "🎨 Fix 3: Frontend Container Test"
echo "--------------------------------"

echo "📋 Testing frontend container directly..."
docker compose exec frontend curl -I http://localhost/ 2>/dev/null || echo "❌ Frontend not responding internally"

echo "📋 Checking frontend nginx configuration..."
docker compose exec frontend nginx -t 2>/dev/null || echo "❌ Frontend nginx config has errors"

echo "📋 Checking what's serving on port 80 in frontend..."
docker compose exec frontend netstat -tlnp 2>/dev/null || echo "❌ Cannot check frontend ports"

echo "🔄 Restarting frontend container..."
docker compose restart frontend

echo "⏳ Waiting for frontend to start..."
sleep 5

echo "📋 Testing frontend after restart..."
if curl -s -f http://localhost/ >/dev/null 2>&1; then
    echo "✅ Frontend is now responding!"
else
    echo "❌ Frontend still not responding"
    echo "📋 Frontend logs after restart:"
    docker compose logs frontend --tail=10
fi

echo ""

# Fix 4: Test Overall Connectivity
echo "🔗 Fix 4: Overall Connectivity Test"
echo "---------------------------------"

echo "📋 Testing all services status..."
docker compose ps

echo ""
echo "📋 Testing end-to-end connectivity..."
echo "API Health: $(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health 2>/dev/null || echo "FAILED")"
echo "Frontend Direct: $(curl -s -o /dev/null -w "%{http_code}" http://localhost/ 2>/dev/null || echo "FAILED")"
echo "External Website: $(curl -s -o /dev/null -w "%{http_code}" https://forestguard.freedynamicdns.org/ 2>/dev/null || echo "FAILED")"

echo ""

# Fix 5: SSL Certificate Status
echo "🔒 Fix 5: SSL Certificate Status"
echo "------------------------------"

echo "📋 Checking certbot directory..."
ls -la ./certbot/conf/ 2>/dev/null || echo "❌ Certbot directory not found"

echo "📋 Looking for certificate files..."
find ./certbot -name "*.crt" -o -name "*.pem" 2>/dev/null | head -5 || echo "❌ No certificate files found"

echo "📋 Current nginx SSL configuration..."
docker compose exec nginx cat /etc/nginx/nginx.conf | grep -A 10 -B 5 "ssl" 2>/dev/null || echo "❌ Cannot read SSL config"

echo ""

# Summary and Next Steps
echo "📊 Fix Summary"
echo "=============="

echo "🎯 Services Status:"
docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "(frontend|api|nginx)"

echo ""
echo "🔧 If issues persist, try these commands:"
echo ""
echo "# Full restart (last resort):"
echo "docker compose down"
echo "docker compose up -d"
echo ""
echo "# Check container networks:"
echo "docker network ls"
echo "docker network inspect wildfire-recovery-argentina_forestguard"
echo ""
echo "# Manual API test:"
echo "docker compose exec api python -c 'import main; print(\"API OK\")'"
echo ""
echo "# Manual nginx test:"
echo "docker compose exec nginx wget -qO- http://api:8000/health"

echo ""
echo "✅ Critical fixes applied!"
echo "📝 Check the results above and run any additional commands if needed"
