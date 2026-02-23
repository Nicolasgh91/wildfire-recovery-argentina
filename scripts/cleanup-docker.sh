#!/bin/bash
# =============================================================================
# FORESTGUARD - Docker Cleanup Script
# =============================================================================
# This script safely cleans up Docker resources to free disk space
# while preserving running containers and important volumes.

set -euo pipefail

echo "=== ForestGuard Docker Cleanup ==="
echo "Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo ""

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo "ERROR: Docker daemon is not running"
    exit 1
fi

echo "=== Before Cleanup - Disk Usage ==="
df -h /
echo ""
docker system df
echo ""

echo "=== Step 1: Remove stopped containers ==="
STOPPED_CONTAINERS=$(docker ps -a -q --filter "status=exited")
if [ -n "$STOPPED_CONTAINERS" ]; then
    echo "Found stopped containers, removing..."
    docker rm $STOPPED_CONTAINERS
else
    echo "No stopped containers found"
fi
echo ""

echo "=== Step 2: Remove unused images (dangling) ==="
docker image prune -f
echo ""

echo "=== Step 3: Remove unused networks ==="
docker network prune -f
echo ""

echo "=== Step 4: Remove BuildKit cache ==="
docker builder prune -af
echo ""

echo "=== Step 5: Remove unused volumes (EXCEPT redis_data) ==="
# Get all unused volumes except redis_data
UNUSED_VOLUMES=$(docker volume ls -q --filter "dangling=true" | grep -v "forestguard_redis_data" || true)
if [ -n "$UNUSED_VOLUMES" ]; then
    echo "Found unused volumes (excluding redis_data), removing..."
    docker volume rm $UNUSED_VOLUMES
else
    echo "No unused volumes found"
fi
echo ""

echo "=== Step 6: Aggressive cleanup (safe for production) ==="
# This removes all unused images, not just dangling ones
# BUT preserves images used by running containers
docker image prune -af
echo ""

echo "=== After Cleanup - Disk Usage ==="
df -h /
echo ""
docker system df
echo ""

echo "=== Current running containers ==="
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Image}}"
echo ""

echo "=== Cleanup Complete ==="
echo "Space freed successfully!"
echo ""
echo "Note: If disk is still >85% full, consider:"
echo "1. Checking for large files outside Docker"
echo "2. Optimizing application Dockerfiles"
echo "3. Implementing log rotation"
echo "4. Moving to larger VM instance"
