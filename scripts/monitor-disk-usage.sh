#!/bin/bash
# =============================================================================
# FORESTGUARD - Disk Usage Monitoring Script
# =============================================================================
# This script monitors disk usage and provides alerts/recommendations
# Can be run manually or as a cron job for proactive monitoring

set -euo pipefail

# Configuration
ALERT_THRESHOLD=80
WARNING_THRESHOLD=70
LOG_FILE="/home/opc/logs/disk-monitor.log"

# Ensure log directory exists
mkdir -p "$(dirname "$LOG_FILE")"

# Function to log with timestamp
log() {
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $1" | tee -a "$LOG_FILE"
}

log "=== Disk Usage Monitoring Started ==="

# Get disk usage
DISK_USE=$(df / | awk 'NR==2 {gsub("%","",$5); print $5}')
DISK_AVAILABLE=$(df -h / | awk 'NR==2 {print $4}')

log "Root filesystem: ${DISK_USE}% used (${DISK_AVAILABLE} available)"

# Docker system usage
if docker info >/dev/null 2>&1; then
    DOCKER_TOTAL=$(docker system df --format "{{.Type}}" | head -1)
    log "Docker system is responsive"
    
    # Get Docker usage breakdown
    DOCKER_IMAGES_SIZE=$(docker system df --format "{{.Size}}" | head -1)
    log "Docker images size: ${DOCKER_IMAGES_SIZE}"
else
    log "WARNING: Docker daemon is not responsive"
fi

# Alert based on usage
if [[ "$DISK_USE" -gt "$ALERT_THRESHOLD" ]]; then
    log "🚨 ALERT: Disk usage is ${DISK_USE}% (threshold: ${ALERT_THRESHOLD}%)"
    log "IMMEDIATE ACTION REQUIRED:"
    log "1. Run: ./scripts/cleanup-docker.sh"
    log "2. Run: docker system prune -af --volumes"
    log "3. Consider moving to larger VM instance"
    
    # Send alert (could be extended to email/slack)
    echo "CRITICAL: VM disk usage at ${DISK_USE}%" >> /tmp/disk_alert
    
elif [[ "$DISK_USE" -gt "$WARNING_THRESHOLD" ]]; then
    log "⚠️  WARNING: Disk usage is ${DISK_USE}% (threshold: ${WARNING_THRESHOLD}%)"
    log "RECOMMENDED ACTIONS:"
    log "1. Run: docker system prune -f"
    log "2. Check for large unused images: docker images | head -10"
    log "3. Monitor trending usage"
    
else
    log "✅ Disk usage is acceptable: ${DISK_USE}%"
fi

# Check for large individual files/directories
log "=== Top 10 largest directories in /home/opc ==="
du -sh /home/opc/* 2>/dev/null | sort -hr | head -10 | while read size path; do
    log "  ${size}  ${path}"
done

# Docker-specific checks
if docker info >/dev/null 2>&1; then
    log "=== Docker Usage Details ==="
    
    # Large images
    log "Top 5 largest Docker images:"
    docker images --format "{{.Repository}}:{{.Tag}}\t{{.Size}}" | sort -k2 -hr | head -5 | while read line; do
        log "  $line"
    done
    
    # Unused images count
    UNUSED_IMAGES=$(docker images -f "dangling=true" -q | wc -l)
    log "Unused (dangling) images: $UNUSED_IMAGES"
    
    # Stopped containers
    STOPPED_CONTAINERS=$(docker ps -a -f "status=exited" -q | wc -l)
    log "Stopped containers: $STOPPED_CONTAINERS"
fi

log "=== Monitoring Complete ==="
echo ""

# Exit with appropriate code for automation
if [[ "$DISK_USE" -gt "$ALERT_THRESHOLD" ]]; then
    exit 2  # Critical
elif [[ "$DISK_USE" -gt "$WARNING_THRESHOLD" ]]; then
    exit 1  # Warning
else
    exit 0  # OK
fi
