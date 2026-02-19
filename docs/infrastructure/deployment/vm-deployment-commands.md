# VM Deployment Commands - CI-Built Frontend Image

## Deploy Entrypoint Oficial (VM)

```bash
# Siempre usar el deploy versionado del repo
cd /home/opc
./scripts/deploy.sh
```

Si existe un script legacy en raiz (`/home/opc/deploy.sh`) neutralizarlo:

```bash
cd /home/opc
test -f ./deploy.sh && mv ./deploy.sh ./deploy.sh.legacy.$(date +%Y%m%d_%H%M%S) || true
chmod +x scripts/deploy.sh scripts/setup-ssl.sh scripts/renew-ssl.sh scripts/renew-ssl-cron.sh scripts/verify-ssl.sh
```

## Phase 1: Current Container Status Verification

### 1.1 Check All Running Containers
```bash
# List all containers with status
docker ps -a

# Show detailed container information
docker compose ps

# Check resource usage
docker stats --no-stream

# Check frontend container specifically
docker ps | grep frontend
```

### 1.2 Verify Current Frontend Configuration
```bash
# Check current frontend image
docker images | grep frontend

# Check if using local build or override
ls -la docker-compose.override.yml

# Check current docker-compose frontend config
grep -A 10 "frontend:" docker-compose.yml

# Check container logs for any issues
docker logs forestguard-frontend --tail 50
```

### 1.3 System Resource Assessment
```bash
# Check memory usage
free -h

# Check disk space
df -h

# Check Docker system usage
docker system df

# Check system load
uptime
```

## Phase 2: Pre-Deployment Preparation

### 2.1 Backup Current Configuration
```bash
# Create backup directory
mkdir -p ~/deployment-backup/$(date +%Y%m%d_%H%M%S)
BACKUP_DIR=~/deployment-backup/$(date +%Y%m%d_%H%M%S)

# Backup docker-compose files
cp docker-compose.yml $BACKUP_DIR/
cp docker-compose.override.yml $BACKUP_DIR/ 2>/dev/null || true

# Save current container state
docker compose ps > $BACKUP_DIR/container-status.txt
docker images > $BACKUP_DIR/images-list.txt

echo "Backup created at: $BACKUP_DIR"
```

### 2.2 Pull and Verify New Image
```bash
# Pull the latest CI-built image
docker pull ghcr.io/nicolasgh91/wildfire-recovery-argentina/frontend:latest

# Verify image details
docker images ghcr.io/nicolasgh91/wildfire-recovery-argentina/frontend

# Check image size (should be ~20-50 MB)
docker image inspect ghcr.io/nicolasgh91/wildfire-recovery-argentina/frontend:latest --format='{{.Size}}'

# Test image locally (optional)
docker run --rm -p 8888:80 --name frontend-test ghcr.io/nicolasgh91/wildfire-recovery-argentina/frontend:latest &
sleep 5
curl -s -o /dev/null -w "%{http_code}" http://localhost:8888/
docker stop frontend-test
```

### 2.3 Update Configuration
```bash
# Rename override file to disable local build
mv docker-compose.override.yml docker-compose.override.yml.backup

# Update docker-compose.yml to use CI image
# Edit the frontend section to replace build with image:
sed -i 's/    build:/    # build:/' docker-compose.yml
sed -i '/^    context: \/frontend$/,/^    dockerfile: Dockerfile$/s/^/    # /' docker-compose.yml

# Add image reference after the commented build section
sed -i '/^    # dockerfile: Dockerfile$/a\    image: ghcr.io/nicolasgh91/wildfire-recovery-argentina/frontend:latest' docker-compose.yml

# Verify the changes
grep -A 15 "frontend:" docker-compose.yml
```

## Phase 3: Deployment Process

### 3.1 Graceful Shutdown
```bash
# Stop frontend container gracefully
docker compose stop frontend

# Verify other services are still running
docker compose ps

# Check for any dependency issues
docker compose logs api --tail 10
```

### 3.2 Deploy New Image
```bash
# Pull latest image (ensure we have the newest version)
docker pull ghcr.io/nicolasgh91/wildfire-recovery-argentina/frontend:latest

# Start frontend with new image
docker compose up -d frontend

# Wait for container to be ready
sleep 10

# Check container status
docker compose ps frontend
```

### 3.3 Post-Deployment Verification
```bash
# Check container logs
docker logs forestguard-frontend --tail 20

# Verify container is running
docker ps | grep frontend

# Check resource usage
docker stats --no-stream | grep frontend

# Verify frontend is serving content
curl -s -o /dev/null -w "%{http_code}" http://localhost/
```

## Phase 4: Validation and Monitoring

### 4.1 Functional Testing
```bash
# Test main frontend routes
curl -s -o /dev/null -w "Main page: %{http_code}\n" http://localhost/
curl -s -o /dev/null -w "SPA route: %{http_code}\n" http://localhost/dashboard
curl -s -o /dev/null -w "Non-existent route: %{http_code}\n" http://localhost/non-existent-route

# Test API connectivity
curl -s -o /dev/null -w "API health: %{http_code}\n" http://localhost/api/health

# Check static assets
curl -s -o /dev/null -w "Static asset: %{http_code}\n" http://localhost/assets/index.js
```

### 4.2 Performance Monitoring
```bash
# Monitor memory usage (should be < 64MB)
watch -n 2 'docker stats --no-stream | grep frontend'

# Check response times
time curl -s http://localhost/ > /dev/null

# Verify nginx configuration safely
docker compose ps --status running --services | grep -q '^nginx$' \
  && docker compose exec -T nginx nginx -t \
  || (echo "nginx is not running" && docker compose logs nginx --tail=100)

# Check image size in use
docker images forestguard-frontend --format "table {{.Repository}}:{{.Tag}}\t{{.Size}}"
```

### 4.3 Rollback Plan (if needed)
```bash
# If issues occur, rollback to local build:
# Stop current frontend
docker compose stop frontend

# Restore override file
mv docker-compose.override.yml.backup docker-compose.override.yml

# Restore original docker-compose.yml
git checkout docker-compose.yml

# Rebuild locally
docker compose build --no-cache frontend
docker compose up -d frontend

# Verify rollback
docker compose ps frontend
docker logs forestguard-frontend --tail 10
```

## Success Indicators

✅ **Container Status**: Frontend container running healthy
✅ **Memory Usage**: Under 64MB as configured
✅ **HTTP Responses**: All routes return 200 (SPA fallback for non-existent)
✅ **Static Assets**: JavaScript and CSS files load correctly
✅ **API Connectivity**: Frontend can communicate with backend API
✅ **Image Source**: Using GHCR image (not local build)

## Troubleshooting Commands

```bash
# If container won't start
docker logs forestguard-frontend --tail 50
docker compose logs frontend

# If image pull fails
docker logout ghcr.io
docker login ghcr.io
docker pull ghcr.io/nicolasgh91/wildfire-recovery-argentina/frontend:latest

# If networking issues
docker network ls
docker network inspect wildfire-recovery-argentina_forestguard

# SSL check and renewal (Docker Certbot mode)
docker compose --profile ssl run --rm certbot certificates
docker compose --profile ssl run --rm certbot renew --webroot --webroot-path=/var/www/certbot
docker compose exec -T nginx nginx -s reload || docker compose restart nginx

# If memory issues
docker system prune -f
docker compose restart frontend
```

## Verification Checklist

- [ ] Frontend container running and healthy
- [ ] Memory usage < 64MB
- [ ] Main page returns 200
- [ ] SPA routes return 200 (fallback)
- [ ] Static assets loading
- [ ] API connectivity working
- [ ] Using GHCR image (not local build)
- [ ] No errors in container logs
- [ ] Other services still running normally
