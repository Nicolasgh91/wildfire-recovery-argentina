#!/bin/bash
# =============================================================================
# FORESTGUARD - Monitor Disk Usage
# =============================================================================
#
# Checks disk usage against configurable thresholds and outputs status/alerts.
# Designed for integration with cron or systemd timers.
#
# Usage:
#   ./scripts/monitor-disk-usage.sh                    # Default thresholds
#   ./scripts/monitor-disk-usage.sh --warn 60 --crit 80
#   ./scripts/monitor-disk-usage.sh --json             # JSON output for tooling
#
# Exit codes:
#   0 — OK (below warning threshold)
#   1 — WARNING (above warning, below critical)
#   2 — CRITICAL (above critical threshold)
#
# Cron example (check every 6 hours):
#   0 */6 * * * /home/opc/scripts/monitor-disk-usage.sh >> /var/log/forestguard-disk.log 2>&1
#
# =============================================================================

set -euo pipefail

WARN_THRESHOLD=70
CRIT_THRESHOLD=85
JSON_OUTPUT=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --warn)  WARN_THRESHOLD="$2"; shift 2 ;;
        --crit)  CRIT_THRESHOLD="$2"; shift 2 ;;
        --json)  JSON_OUTPUT=true; shift ;;
        --help|-h)
            echo "Usage: $0 [--warn N] [--crit N] [--json]"
            echo ""
            echo "  --warn N   Warning threshold percentage (default: 70)"
            echo "  --crit N   Critical threshold percentage (default: 85)"
            echo "  --json     Output in JSON format"
            echo ""
            echo "Exit codes: 0=OK, 1=WARNING, 2=CRITICAL"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
DISK_USE=$(df / | awk 'NR==2 {gsub("%","",$5); print $5}')
DISK_AVAIL=$(df -h / | awk 'NR==2 {print $4}')
DISK_TOTAL=$(df -h / | awk 'NR==2 {print $2}')

# Determine status
if [ "$DISK_USE" -gt "$CRIT_THRESHOLD" ]; then
    STATUS="CRITICAL"
    EXIT_CODE=2
elif [ "$DISK_USE" -gt "$WARN_THRESHOLD" ]; then
    STATUS="WARNING"
    EXIT_CODE=1
else
    STATUS="OK"
    EXIT_CODE=0
fi

# Docker metrics (best-effort)
DOCKER_IMAGES_SIZE=$(docker system df --format '{{.Size}}' 2>/dev/null | head -1 || echo "unknown")
DOCKER_CONTAINERS_SIZE=$(docker system df --format '{{.Size}}' 2>/dev/null | sed -n '2p' || echo "unknown")
DOCKER_VOLUMES_SIZE=$(docker system df --format '{{.Size}}' 2>/dev/null | sed -n '3p' || echo "unknown")
DOCKER_BUILDCACHE_SIZE=$(docker system df --format '{{.Size}}' 2>/dev/null | sed -n '4p' || echo "unknown")

if $JSON_OUTPUT; then
    cat <<EOF
{
  "timestamp": "$TIMESTAMP",
  "status": "$STATUS",
  "disk_use_percent": $DISK_USE,
  "disk_available": "$DISK_AVAIL",
  "disk_total": "$DISK_TOTAL",
  "warn_threshold": $WARN_THRESHOLD,
  "crit_threshold": $CRIT_THRESHOLD,
  "docker": {
    "images_size": "$DOCKER_IMAGES_SIZE",
    "containers_size": "$DOCKER_CONTAINERS_SIZE",
    "volumes_size": "$DOCKER_VOLUMES_SIZE",
    "buildcache_size": "$DOCKER_BUILDCACHE_SIZE"
  }
}
EOF
else
    echo "[$TIMESTAMP] Disk Monitor: $STATUS"
    echo "  Filesystem: ${DISK_USE}% used (${DISK_AVAIL} available of ${DISK_TOTAL})"
    echo "  Thresholds: warn=${WARN_THRESHOLD}%, crit=${CRIT_THRESHOLD}%"
    echo "  Docker images:      $DOCKER_IMAGES_SIZE"
    echo "  Docker containers:  $DOCKER_CONTAINERS_SIZE"
    echo "  Docker volumes:     $DOCKER_VOLUMES_SIZE"
    echo "  Docker build cache: $DOCKER_BUILDCACHE_SIZE"

    if [ "$EXIT_CODE" -gt 0 ]; then
        echo ""
        echo "Recommended actions:"
        if [ "$EXIT_CODE" -eq 2 ]; then
            echo "  IMMEDIATE: ./scripts/emergency-disk-cleanup.sh --force"
        fi
        echo "  1. Run: ./scripts/analyze-disk-usage.sh"
        echo "  2. Run: ./scripts/cleanup-docker.sh --aggressive"
    fi
fi

exit $EXIT_CODE
