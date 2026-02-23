#!/bin/bash
# =============================================================================
# FORESTGUARD - Analyze Disk Usage
# =============================================================================
#
# Provides a detailed breakdown of disk usage on the VM, focused on Docker
# resources (images, containers, volumes, BuildKit cache) and system-level
# directories.
#
# Usage:
#   ./scripts/analyze-disk-usage.sh
#
# =============================================================================

set -euo pipefail

BOLD='\033[1m'
RESET='\033[0m'
YELLOW='\033[33m'
RED='\033[31m'

section() {
    echo ""
    echo -e "${BOLD}=== $1 ===${RESET}"
}

# ── 1. General disk usage ───────────────────────────────────────
section "Filesystem Usage"
df -h /

DISK_USE=$(df / | awk 'NR==2 {gsub("%","",$5); print $5}')
if [ "$DISK_USE" -gt 85 ]; then
    echo -e "${RED}CRITICAL: Disk is ${DISK_USE}% full${RESET}"
elif [ "$DISK_USE" -gt 70 ]; then
    echo -e "${YELLOW}WARNING: Disk is ${DISK_USE}% full${RESET}"
else
    echo "Disk usage is healthy (${DISK_USE}%)"
fi

# ── 2. Docker system overview ──────────────────────────────────
section "Docker System Disk Usage"
docker system df 2>/dev/null || echo "(Docker daemon not available)"

section "Docker System Disk Usage (verbose)"
docker system df -v 2>/dev/null || echo "(Docker daemon not available)"

# ── 3. Docker images ───────────────────────────────────────────
section "Docker Images (sorted by size)"
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedSince}}" 2>/dev/null \
    | head -30 || echo "(no images found)"

# ── 4. Docker containers ──────────────────────────────────────
section "Docker Containers (all)"
docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Size}}" 2>/dev/null \
    || echo "(no containers found)"

# ── 5. Docker volumes ─────────────────────────────────────────
section "Docker Volumes"
docker volume ls 2>/dev/null || echo "(no volumes found)"

echo ""
echo "Volume sizes:"
for vol in $(docker volume ls -q 2>/dev/null); do
    SIZE=$(docker system df -v 2>/dev/null | grep "$vol" | awk '{print $NF}' || echo "unknown")
    echo "  $vol: $SIZE"
done

# ── 6. BuildKit cache ─────────────────────────────────────────
section "BuildKit Cache"
docker builder du 2>/dev/null || echo "(BuildKit cache info not available)"

# ── 7. Top directories by size ────────────────────────────────
APP_DIR="${APP_DIR:-/home/opc}"
section "Top 15 Directories by Size (${APP_DIR})"
if [ -d "$APP_DIR" ]; then
    du -h --max-depth=2 "$APP_DIR" 2>/dev/null | sort -rh | head -15
else
    echo "(Directory $APP_DIR not found, using current directory)"
    du -h --max-depth=2 . 2>/dev/null | sort -rh | head -15
fi

# ── 8. Docker log sizes ──────────────────────────────────────
section "Docker Container Log Sizes"
LOG_DIR="/var/lib/docker/containers"
if [ -d "$LOG_DIR" ] && [ -r "$LOG_DIR" ]; then
    find "$LOG_DIR" -name "*.log" -exec du -h {} \; 2>/dev/null | sort -rh | head -10
else
    echo "(Cannot access $LOG_DIR — may need sudo)"
    # Fallback: show log sizes via docker inspect
    for cid in $(docker ps -q 2>/dev/null); do
        NAME=$(docker inspect --format '{{.Name}}' "$cid" 2>/dev/null | sed 's|^/||')
        LOG_PATH=$(docker inspect --format '{{.LogPath}}' "$cid" 2>/dev/null || true)
        if [ -n "$LOG_PATH" ] && [ -f "$LOG_PATH" ]; then
            LOG_SIZE=$(du -h "$LOG_PATH" 2>/dev/null | cut -f1 || echo "unknown")
            echo "  $NAME: $LOG_SIZE"
        fi
    done
fi

# ── 9. Summary ────────────────────────────────────────────────
section "Summary"
echo "Disk usage: ${DISK_USE}%"
IMAGES_COUNT=$(docker images -q 2>/dev/null | wc -l || echo 0)
CONTAINERS_COUNT=$(docker ps -aq 2>/dev/null | wc -l || echo 0)
RUNNING_COUNT=$(docker ps -q 2>/dev/null | wc -l || echo 0)
VOLUMES_COUNT=$(docker volume ls -q 2>/dev/null | wc -l || echo 0)
echo "Docker images: $IMAGES_COUNT"
echo "Docker containers: $CONTAINERS_COUNT (running: $RUNNING_COUNT)"
echo "Docker volumes: $VOLUMES_COUNT"
echo ""

if [ "$DISK_USE" -gt 75 ]; then
    echo "Recommended actions:"
    echo "  1. Run: ./scripts/cleanup-docker.sh"
    echo "  2. If still high: ./scripts/cleanup-docker.sh --aggressive"
    echo "  3. Emergency: ./scripts/emergency-disk-cleanup.sh"
fi
