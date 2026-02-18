#!/bin/bash

# VM Analysis & Troubleshooting Script
# Run this on the VM: ssh -i "llave" opc@141.148.54.223
# Usage: ./vm-analysis-script.sh

set -e

echo "🔍 VM Analysis & Troubleshooting Script"
echo "======================================"
echo "Website: https://forestguard.freedynamicdns.org/"
echo ""

# Phase 1: Basic System Status
echo "📊 Phase 1: Basic System Status"
echo "-------------------------------"

echo "🖥️  System Info:"
uname -a
echo ""

echo "💾 Memory Usage:"
free -h
echo ""

echo "💿 Disk Usage:"
df -h
echo ""

echo "🔥 CPU Load:"
uptime
echo ""

echo "🐳 Docker Status:"
systemctl is-active docker
docker --version
echo ""

# Phase 2: Container Analysis
echo "🏗️  Phase 2: Container Analysis"
echo "------------------------------"

echo "📦 All Containers Status:"
docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}\t{{.Image}}"
echo ""

echo "📋 Docker Compose Status:"
docker compose ps
echo ""

echo "📈 Container Resource Usage:"
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}"
echo ""

# Phase 3: Service-by-Service Health Checks
echo "🔧 Phase 3: Service Health Checks"
echo "--------------------------------"

echo "🔴 Redis Health:"
if docker compose exec -T redis redis-cli ping 2>/dev/null; then
    echo "✅ Redis is responding"
else
    echo "❌ Redis is not responding"
fi
echo ""

echo "🔧 API Health:"
if curl -s -f http://localhost:8000/health >/dev/null 2>&1; then
    echo "✅ API health check passed"
    curl -s http://localhost:8000/health | head -1
else
    echo "❌ API health check failed"
fi
echo ""

echo "🌸 Flower Monitoring:"
if curl -s -f http://localhost:5555/ >/dev/null 2>&1; then
    echo "✅ Flower is accessible"
else
    echo "❌ Flower is not accessible"
fi
echo ""

echo "🎨 Frontend Direct:"
if curl -s -f http://localhost/ >/dev/null 2>&1; then
    echo "✅ Frontend responding directly"
else
    echo "❌ Frontend not responding directly"
fi
echo ""

# Phase 4: Network & Port Analysis
echo "🌐 Phase 4: Network & Port Analysis"
echo "---------------------------------"

echo "🔌 Listening Ports:"
netstat -tlnp 2>/dev/null | grep -E ':(80|443|8000|5555|6379)' || ss -tlnp | grep -E ':(80|443|8000|5555|6379)'
echo ""

echo "🔥 Firewall Rules (iptables):"
sudo iptables -L -n | grep -E '(ACCEPT|DROP|REJECT)' | head -10
echo ""

echo "🔍 External Connectivity Test:"
echo "Testing from VM to external website..."
if curl -s -I https://forestguard.freedynamicdns.org/ >/dev/null 2>&1; then
    echo "✅ External website accessible from VM"
else
    echo "❌ External website NOT accessible from VM"
fi
echo ""

# Phase 5: Container Logs Analysis
echo "📋 Phase 5: Critical Container Logs"
echo "---------------------------------"

echo "🌐 Nginx Logs (last 10 lines):"
docker compose logs --tail=10 nginx 2>/dev/null || echo "No nginx logs found"
echo ""

echo "🎨 Frontend Logs (last 10 lines):"
docker compose logs --tail=10 frontend 2>/dev/null || echo "No frontend logs found"
echo ""

echo "🔧 API Logs (last 10 lines):"
docker compose logs --tail=10 api 2>/dev/null || echo "No api logs found"
echo ""

# Phase 6: SSL Certificate Check
echo "🔒 Phase 6: SSL Certificate Analysis"
echo "-----------------------------------"

echo "📜 SSL Certificate Info:"
if [ -d ./certbot/conf ]; then
    echo "Certbot directory exists"
    find ./certbot/conf -name "*.crt" -exec echo "Certificate: {}" \; -exec openssl x509 -in {} -text -noout | grep -E "(Not Before|Not After)" \;
else
    echo "❌ Certbot directory not found"
fi
echo ""

echo "🔍 HTTPS Test:"
echo "Testing HTTPS connection..."
if timeout 10 openssl s_client -connect forestguard.freedynamicdns.org:443 -servername forestguard.freedynamicdns.org </dev/null 2>/dev/null | grep -q "Verify return code: 0"; then
    echo "✅ SSL certificate is valid"
else
    echo "❌ SSL certificate issue detected"
fi
echo ""

# Phase 7: Inter-Container Communication
echo "🔗 Phase 7: Inter-Container Communication"
echo "----------------------------------------"

echo "🎨 Frontend → API:"
if docker compose exec -T frontend curl -s -f http://api:8000/health >/dev/null 2>&1; then
    echo "✅ Frontend can reach API"
else
    echo "❌ Frontend cannot reach API"
fi
echo ""

echo "🔧 API → Redis:"
if docker compose exec -T api python -c "import redis; r=redis.Redis(host='redis'); print('Redis OK:' + str(r.ping()))" 2>/dev/null; then
    echo "✅ API can reach Redis"
else
    echo "❌ API cannot reach Redis"
fi
echo ""

# Phase 8: Recent System Events
echo "📅 Phase 8: Recent System Events"
echo "-----------------------------"

echo "🔄 Recent Docker Events:"
docker events --since 1h --format "{{.Time}} {{.Action}} {{.Actor.Attributes.name}}" 2>/dev/null | tail -10 || echo "No recent Docker events"
echo ""

echo "📋 System Journal (docker related):"
sudo journalctl --since 1h -u docker.service --no-pager | tail -5
echo ""

# Summary & Recommendations
echo "📊 Summary & Recommendations"
echo "==========================="

echo "🎯 Critical Issues Found:"
ISSUES_FOUND=0

# Check if nginx is running
if ! docker ps --format "{{.Names}}" | grep -q "forestguard-nginx"; then
    echo "❌ Nginx container is not running"
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
fi

# Check if frontend is running
if ! docker ps --format "{{.Names}}" | grep -q "forestguard-frontend"; then
    echo "❌ Frontend container is not running"
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
fi

# Check if API is running
if ! docker ps --format "{{.Names}}" | grep -q "forestguard-api"; then
    echo "❌ API container is not running"
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
fi

# Check external access
if ! curl -s -I https://forestguard.freedynamicdns.org/ >/dev/null 2>&1; then
    echo "❌ External website not accessible"
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
fi

if [ $ISSUES_FOUND -eq 0 ]; then
    echo "✅ No critical issues detected"
else
    echo "🚨 Found $ISSUES_FOUND critical issues"
fi

echo ""
echo "🔧 Quick Fix Commands:"
echo "---------------------"
echo "# Restart all services:"
echo "docker compose restart"
echo ""
echo "# Restart specific service:"
echo "docker compose restart [service-name]"
echo ""
echo "# View detailed logs:"
echo "docker compose logs -f [service-name]"
echo ""
echo "# Check container health:"
echo "docker compose ps"
echo ""

echo "🌐 Access URLs:"
echo "---------------"
echo "Website: https://forestguard.freedynamicdns.org/"
echo "API: http://141.148.54.223:8000/health"
echo "Flower: http://141.148.54.223:5555/"
echo ""

echo "✅ Analysis complete!"
echo "📝 Save this output for troubleshooting reference"
