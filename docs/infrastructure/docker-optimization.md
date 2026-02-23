# Docker Optimization Guide

This document outlines strategies to optimize Docker image sizes and reduce disk usage on the production VM.

## Current Issues

The production VM is experiencing disk space issues due to:
- Large Docker images (multiple Python containers with scientific computing packages)
- Accumulation of unused images between deploys
- BuildKit cache buildup
- Inefficient layer caching

## Implemented Optimizations

### 1. Multi-Stage Builds
- **Dockerfile.api** and **Dockerfile.worker** now use multi-stage builds
- Build dependencies are excluded from runtime images
- Reduces final image size by ~200-400MB per image

### 2. Enhanced Cleanup Automation
- **deploy-prod-vm.yml** includes automatic cleanup before each deploy
- **deploy.sh** performs pre-build cleanup
- Removes BuildKit cache, dangling images, and stopped containers

### 3. Improved .dockerignore
- Excludes unnecessary files from build context
- Reduces build time and layer sizes
- Prevents accidental inclusion of secrets and temp files

### 4. Monitoring Scripts
- **analyze-disk-usage.sh**: Comprehensive disk usage analysis
- **cleanup-docker.sh**: Safe Docker resource cleanup
- **monitor-disk-usage.sh**: Proactive monitoring with alerts

## Usage Instructions

### Immediate Cleanup
```bash
# On the production VM
./scripts/cleanup-docker.sh
```

### Disk Usage Analysis
```bash
# Analyze current disk usage
./scripts/analyze-disk-usage.sh
```

### Monitoring
```bash
# Check current disk status
./scripts/monitor-disk-usage.sh
```

### Manual Cleanup (if needed)
```bash
# Aggressive cleanup (removes all unused images + volumes)
docker system prune -af --volumes

# Remove BuildKit cache
docker builder prune -af
```

## Expected Results

### Image Size Reductions
- **API image**: ~200MB smaller
- **Worker images**: ~200MB smaller each
- **Total savings**: ~1.2GB across all Python containers

### Disk Space Recovery
- **BuildKit cache**: 500MB-2GB
- **Unused images**: 1-3GB
- **Stopped containers**: 100-500MB

### Ongoing Benefits
- **Faster builds**: Smaller build context
- **Faster deploys**: Less data to transfer
- **Stable disk usage**: Automated cleanup prevents accumulation

## Best Practices

### Development
1. Use `docker system prune -f` regularly during development
2. Monitor image sizes with `docker images`
3. Use multi-stage builds for all new services

### Production
1. Automated cleanup runs before each deploy
2. Monitor disk usage weekly with monitoring script
3. Set up cron job for proactive monitoring:
   ```bash
   # Add to crontab for daily monitoring
   0 6 * * * /home/opc/scripts/monitor-disk-usage.sh
   ```

### Long-term Optimizations
1. Consider shared base images for Python services
2. Implement image versioning strategy
3. Explore Alpine variants for further size reduction
4. Consider external build cache for faster builds

## Troubleshooting

### Disk Still Full After Cleanup
1. Check for large files outside Docker: `find / -size +1G 2>/dev/null`
2. Verify Redis volume size: `docker volume inspect forestguard_redis_data`
3. Check log files: `du -sh /var/log/*`

### Build Failures After Optimization
1. Verify all dependencies are in requirements.txt
2. Check .dockerignore isn't excluding needed files
3. Validate multi-stage build copies all necessary components

### Performance Issues
1. Monitor VM resources: `top`, `htop`, `iostat`
2. Check Docker daemon health: `docker info`
3. Verify container resource limits in docker-compose.yml

## Monitoring Setup

### Cron Job for Daily Monitoring
```bash
# Edit crontab
crontab -e

# Add daily monitoring at 6 AM UTC
0 6 * * * /home/opc/scripts/monitor-disk-usage.sh >> /home/opc/logs/disk-monitor.log 2>&1
```

### Alert Thresholds
- **Warning**: 70% disk usage
- **Critical**: 80% disk usage
- **Emergency**: 87% disk usage (deploy blocked)

## Future Improvements

1. **Shared Base Images**: Create common base image for all Python services
2. **Alpine Variants**: Evaluate Alpine Linux for smaller base images
3. **External Registry**: Use external registry for image versioning
4. **Build Cache**: Implement build cache sharing across environments
5. **Resource Limits**: Set memory/CPU limits in docker-compose.yml
