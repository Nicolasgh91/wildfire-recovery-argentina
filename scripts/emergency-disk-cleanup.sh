#!/bin/bash
# =============================================================================
# FORESTGUARD - Emergency Disk Cleanup Script
# =============================================================================
# This script performs aggressive cleanup to immediately resolve disk space issues
# Run this when VM is at 87%+ disk usage and deploy is failing

set -euo pipefail

echo "🚨 EMERGENCY DISK CLEANUP - ForestGuard VM 🚨"
echo "Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo ""

# Check if running as root or with sudo
if [[ $EUID -ne 0 ]]; then
   echo "This script requires sudo privileges for some operations"
   echo "Running with sudo where needed..."
fi

echo "=== BEFORE CLEANUP - Disk Usage ==="
df -h /
echo ""

echo "=== BEFORE CLEANUP - Docker Usage ==="
docker system df 2>/dev/null || echo "Docker not accessible"
echo ""

echo "⚠️  WARNING: This will perform aggressive cleanup!"
echo "The following will be removed:"
echo "  - All stopped containers"
echo "  - All unused images (not used by running containers)"
echo "  - All BuildKit cache"
echo "  - All unused volumes (EXCEPT redis_data)"
echo "  - System package caches"
echo "  - Log files older than 7 days"
echo ""
read -p "Continue with emergency cleanup? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cleanup cancelled"
    exit 0
fi

echo ""
echo "=== Step 1: Docker Cleanup ==="

# Stop any non-essential containers (keep core services running)
echo "Stopping non-essential containers..."
docker stop $(docker ps -q --filter "name=flower" --filter "name=celery-beat") 2>/dev/null || echo "No optional containers to stop"

# Remove stopped containers
echo "Removing stopped containers..."
docker container prune -f

# Remove BuildKit cache (major space saver)
echo "Removing BuildKit cache..."
docker builder prune -af

# Remove unused images aggressively
echo "Removing unused images..."
docker image prune -af

# Remove unused volumes (protect redis_data)
echo "Removing unused volumes (protecting redis_data)..."
UNUSED_VOLUMES=$(docker volume ls -q --filter "dangling=true" | grep -v "forestguard_redis_data" || true)
if [ -n "$UNUSED_VOLUMES" ]; then
    docker volume rm $UNUSED_VOLUMES
else
    echo "No unused volumes to remove"
fi

echo ""
echo "=== Step 2: System Cleanup ==="

# Clean package caches
echo "Cleaning system package caches..."
if command -v apt-get >/dev/null 2>&1; then
    sudo apt-get clean
    sudo apt-get autoremove -y
fi

# Clean old logs (keep last 7 days)
echo "Cleaning old log files..."
sudo find /var/log -name "*.log" -type f -mtime +7 -delete 2>/dev/null || true
sudo find /var/log -name "*.log.*" -type f -delete 2>/dev/null || true

# Clean temp files
echo "Cleaning temporary files..."
sudo rm -rf /tmp/* 2>/dev/null || true
sudo rm -rf /var/tmp/* 2>/dev/null || true

# Clean application logs
echo "Cleaning application logs..."
find /home/opc/logs -name "*.log" -type f -mtime +7 -delete 2>/dev/null || true

echo ""
echo "=== Step 3: Application Specific Cleanup ==="

# Rotate Redis logs if too large
if docker volume inspect forestguard_redis_data >/dev/null 2>&1; then
    REDIS_MOUNT=$(docker volume inspect forestguard_redis_data --format '{{ .Mountpoint }}')
    if [ -d "$REDIS_MOUNT" ]; then
        REDIS_SIZE=$(sudo du -sh "$REDIS_MOUNT" 2>/dev/null | cut -f1)
        echo "Redis data size: $REDIS_SIZE"
        
        # If Redis data is >1GB, suggest manual intervention
        REDIS_MB=$(sudo du -sm "$REDIS_MOUNT" 2>/dev/null | cut -f1)
        if [[ "$REDIS_MB" -gt 1024 ]]; then
            echo "⚠️  Redis data is large (${REDIS_MB}MB). Consider:"
            echo "  - Redis data cleanup: docker exec forestguard-redis redis-cli FLUSHDB"
            echo "  - Check for Redis memory leaks"
        fi
    fi
fi

echo ""
echo "=== AFTER CLEANUP - Disk Usage ==="
df -h /
echo ""

echo "=== AFTER CLEANUP - Docker Usage ==="
docker system df 2>/dev/null || echo "Docker not accessible"
echo ""

echo "=== Restarting essential services ==="
# Restart any stopped optional services
docker start $(docker ps -a -q --filter "name=flower" --filter "name=celery-beat" --filter "status=exited") 2>/dev/null || echo "No services to restart"

echo ""
echo "=== Cleanup Summary ==="
echo "✅ Emergency cleanup completed!"
echo ""
echo "Next steps:"
echo "1. Check if disk usage is now below 85%"
echo "2. If still high, consider:"
echo "   - Manual Redis cleanup: docker exec forestguard-redis redis-cli FLUSHDB"
echo "   - Moving to larger VM instance"
echo "   - Further application optimization"
echo ""
echo "3. Run deploy again: ./scripts/deploy.sh"
echo "4. Set up monitoring: ./scripts/monitor-disk-usage.sh"

# Final check
FINAL_DISK_USE=$(df / | awk 'NR==2 {gsub("%","",$5); print $5}')
echo ""
echo "Final disk usage: ${FINAL_DISK_USE}%"

if [[ "$FINAL_DISK_USE" -lt 85 ]]; then
    echo "✅ Disk usage is now acceptable - deploy should succeed"
    exit 0
elif [[ "$FINAL_DISK_USE" -lt 90 ]]; then
    echo "⚠️  Disk usage improved but still high - monitor closely"
    exit 1
else
    echo "🚨 Disk usage still critical - immediate action required"
    exit 2
fi
