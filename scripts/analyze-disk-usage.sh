#!/bin/bash
# =============================================================================
# FORESTGUARD - Disk Usage Analysis Script
# =============================================================================
# This script analyzes disk usage on the production VM to identify
# why container images have become so large and what's consuming space.

set -euo pipefail

echo "=== ForestGuard VM Disk Usage Analysis ==="
echo "Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo ""

echo "=== 1. Overall Filesystem Usage ==="
df -h /
echo ""

echo "=== 2. Docker System Overview ==="
docker system df
echo ""

echo "=== 3. Detailed Docker Space Usage ==="
docker system df -v
echo ""

echo "=== 4. Largest Docker Images ==="
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}" | sort -k3 -hr | head -15
echo ""

echo "=== 5. Running Container Sizes ==="
docker ps -s --format "table {{.Names}}\t{{.Status}}\t{{.Size}}" | head -10
echo ""

echo "=== 6. Docker Directory Breakdown ==="
if [ -d /var/lib/docker ]; then
    sudo du -sh /var/lib/docker/* 2>/dev/null | sort -hr | head -10
else
    echo "Docker directory not found at /var/lib/docker"
fi
echo ""

echo "=== 7. BuildKit Cache Size ==="
if [ -d /var/lib/docker/buildkit ]; then
    sudo du -sh /var/lib/docker/buildkit 2>/dev/null || echo "BuildKit cache not accessible"
fi
echo ""

echo "=== 8. Volume Usage ==="
docker volume ls --format "table {{.Name}}\t{{.Driver}}" | head -10
echo ""

echo "=== 9. Redis Volume Size ==="
if docker volume inspect forestguard_redis_data >/dev/null 2>&1; then
    echo "Redis volume mount point:"
    docker volume inspect forestguard_redis_data --format '{{ .Mountpoint }}'
    if [ -d "$(docker volume inspect forestguard_redis_data --format '{{ .Mountpoint }}')" ]; then
        sudo du -sh "$(docker volume inspect forestguard_redis_data --format '{{ .Mountpoint }}')" 2>/dev/null || echo "Cannot access redis volume size"
    fi
else
    echo "Redis volume not found"
fi
echo ""

echo "=== 10. Log Files Size ==="
if [ -d /var/log ]; then
    sudo du -sh /var/log/* 2>/dev/null | sort -hr | head -10
fi
echo ""

echo "=== 11. Application Logs Size ==="
if [ -d /home/opc/logs ]; then
    du -sh /home/opc/logs/* 2>/dev/null | sort -hr | head -10
fi
echo ""

echo "=== 12. Top 15 Largest Directories in /home/opc ==="
du -sh /home/opc/* 2>/dev/null | sort -hr | head -15
echo ""

echo "=== Analysis Complete ==="
echo "Recommendations:"
echo "1. Run 'docker system prune -af --volumes' to clean unused images and volumes"
echo "2. Run 'docker builder prune -af' to clear BuildKit cache"
echo "3. Consider optimizing Dockerfiles for smaller image sizes"
echo "4. Implement automated cleanup in deployment workflow"
