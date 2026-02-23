#!/bin/bash
# =============================================================================
# FORESTGUARD - Emergency Disk Cleanup
# =============================================================================
#
# Aggressively frees disk space by removing ALL unused Docker resources.
# This includes unused images (even recent ones), all BuildKit cache, and
# optionally unused volumes.
#
# WARNING: This will remove ALL Docker resources not currently in use.
# Running containers and their images/volumes are NOT affected.
#
# Usage:
#   ./scripts/emergency-disk-cleanup.sh          # Interactive confirmation
#   ./scripts/emergency-disk-cleanup.sh --force  # No confirmation (for automation)
#
# =============================================================================

set -euo pipefail

FORCE=false

for arg in "$@"; do
    case "$arg" in
        --force)  FORCE=true ;;
        --help|-h)
            echo "Usage: $0 [--force]"
            echo ""
            echo "Aggressively removes ALL unused Docker resources."
            echo "Running containers and their resources are NOT affected."
            echo ""
            echo "  --force   Skip interactive confirmation"
            exit 0
            ;;
        *)
            echo "Unknown option: $arg"
            exit 1
            ;;
    esac
done

RED='\033[31m'
BOLD='\033[1m'
RESET='\033[0m'

echo -e "${RED}${BOLD}=== EMERGENCY DISK CLEANUP ===${RESET}"
echo ""
echo "Current disk usage:"
df -h /
echo ""
echo "Docker resource usage:"
docker system df 2>/dev/null || true
echo ""

if ! $FORCE; then
    echo -e "${RED}This will remove ALL unused Docker resources:${RESET}"
    echo "  - All unused images (not just dangling)"
    echo "  - All stopped containers"
    echo "  - All unused networks"
    echo "  - All BuildKit build cache"
    echo "  - All unused volumes (DATA LOSS risk if volumes contain important data)"
    echo ""
    echo "Running containers and their images/volumes are NOT affected."
    echo ""
    read -r -p "Are you sure? Type 'yes' to continue: " CONFIRM
    if [ "$CONFIRM" != "yes" ]; then
        echo "Aborted."
        exit 0
    fi
fi

DISK_BEFORE=$(df / | awk 'NR==2 {print $4}')

echo ""
echo "Step 1/3: Removing all unused containers, networks, and dangling images..."
docker system prune -af 2>/dev/null || true

echo ""
echo "Step 2/3: Removing ALL BuildKit build cache..."
docker builder prune -af 2>/dev/null || true

echo ""
echo "Step 3/3: Removing unused volumes..."
docker volume prune -f 2>/dev/null || true

DISK_AFTER=$(df / | awk 'NR==2 {print $4}')
RECOVERED_KB=$((DISK_AFTER - DISK_BEFORE))
RECOVERED_MB=$((RECOVERED_KB / 1024))

echo ""
echo -e "${BOLD}=== Cleanup Complete ===${RESET}"
df -h /
echo ""
if [ "$RECOVERED_MB" -gt 0 ]; then
    echo "Recovered approximately ${RECOVERED_MB}MB of disk space."
else
    echo "Minimal space recovered (resources were already clean)."
fi
echo ""
echo "Docker resource usage after cleanup:"
docker system df 2>/dev/null || true
