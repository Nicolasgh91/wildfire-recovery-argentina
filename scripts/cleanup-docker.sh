#!/bin/bash
# =============================================================================
# FORESTGUARD - Docker Cleanup
# =============================================================================
#
# Safe cleanup of Docker resources. By default only removes clearly
# unnecessary items (dangling images, stopped containers, old BuildKit cache).
#
# Usage:
#   ./scripts/cleanup-docker.sh              # Safe cleanup
#   ./scripts/cleanup-docker.sh --aggressive # Also remove unused images >7 days
#   ./scripts/cleanup-docker.sh --dry-run    # Show what would be removed
#
# =============================================================================

set -euo pipefail

AGGRESSIVE=false
DRY_RUN=false

for arg in "$@"; do
    case "$arg" in
        --aggressive) AGGRESSIVE=true ;;
        --dry-run)    DRY_RUN=true ;;
        --help|-h)
            echo "Usage: $0 [--aggressive] [--dry-run]"
            echo ""
            echo "  (default)     Safe cleanup: dangling images, stopped containers, old BuildKit cache"
            echo "  --aggressive  Also remove all unused images older than 7 days"
            echo "  --dry-run     Show what would be removed without executing"
            exit 0
            ;;
        *)
            echo "Unknown option: $arg"
            echo "Run: $0 --help"
            exit 1
            ;;
    esac
done

BOLD='\033[1m'
RESET='\033[0m'

section() {
    echo ""
    echo -e "${BOLD}=== $1 ===${RESET}"
}

# Record disk usage before cleanup
DISK_BEFORE=$(df / | awk 'NR==2 {print $4}')
DISK_BEFORE_H=$(df -h / | awk 'NR==2 {print $4}')

section "Disk Usage Before Cleanup"
df -h /

if $DRY_RUN; then
    echo ""
    echo "[DRY RUN] The following actions would be performed:"
    echo ""
fi

# ── 1. Stopped containers ──────────────────────────────────────
section "Removing stopped containers"
if $DRY_RUN; then
    STOPPED=$(docker ps -a --filter "status=exited" --format "{{.Names}}" 2>/dev/null || true)
    if [ -n "$STOPPED" ]; then
        echo "Would remove: $STOPPED"
    else
        echo "No stopped containers to remove"
    fi
else
    docker container prune -f 2>/dev/null || true
fi

# ── 2. Dangling images ────────────────────────────────────────
section "Removing dangling images"
if $DRY_RUN; then
    DANGLING=$(docker images -f "dangling=true" -q 2>/dev/null | wc -l || echo 0)
    echo "Would remove $DANGLING dangling image(s)"
else
    docker image prune -f 2>/dev/null || true
fi

# ── 3. BuildKit cache ─────────────────────────────────────────
section "Removing BuildKit cache (older than 7 days)"
if $DRY_RUN; then
    echo "Would prune BuildKit cache entries older than 168 hours"
else
    docker builder prune -f --filter "until=168h" 2>/dev/null || true
fi

# ── 4. Aggressive: unused images ──────────────────────────────
if $AGGRESSIVE; then
    section "Removing ALL unused images older than 7 days (aggressive)"
    if $DRY_RUN; then
        UNUSED=$(docker images --filter "dangling=false" --format "{{.Repository}}:{{.Tag}} ({{.Size}}, {{.CreatedSince}})" 2>/dev/null || true)
        echo "Would evaluate these images for removal (unused + older than 7 days):"
        echo "$UNUSED" | head -20
    else
        docker image prune -af --filter "until=168h" 2>/dev/null || true
    fi

    section "Removing ALL BuildKit cache (aggressive)"
    if $DRY_RUN; then
        echo "Would remove entire BuildKit cache"
    else
        docker builder prune -af 2>/dev/null || true
    fi
fi

# ── Summary ────────────────────────────────────────────────────
if ! $DRY_RUN; then
    DISK_AFTER=$(df / | awk 'NR==2 {print $4}')
    DISK_AFTER_H=$(df -h / | awk 'NR==2 {print $4}')
    RECOVERED_KB=$((DISK_AFTER - DISK_BEFORE))

    section "Disk Usage After Cleanup"
    df -h /

    echo ""
    echo "Space before: $DISK_BEFORE_H available"
    echo "Space after:  $DISK_AFTER_H available"
    if [ "$RECOVERED_KB" -gt 0 ]; then
        RECOVERED_MB=$((RECOVERED_KB / 1024))
        echo "Recovered:    ~${RECOVERED_MB}MB"
    else
        echo "Recovered:    minimal (resources were already clean)"
    fi
fi

section "Docker System Summary"
docker system df 2>/dev/null || true
