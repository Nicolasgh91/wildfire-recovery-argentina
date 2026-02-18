# Quick Deployment Commands - Manual Steps

## 🚀 Start All Services & Deploy CI Frontend

### 1. Environment Check
```bash
# Verify prerequisites
docker --version
docker-compose --version
ls -la .env
ls -la ~/.config/gcloud
```

### 2. Start Backend Services
```bash
# Stop any existing services
docker compose down

# Start Redis (required first)
docker compose up -d redis
# Wait for healthy: docker compose logs -f redis

# Start API (depends on Redis)
docker compose up -d api
# Wait for healthy: curl http://localhost:8000/health

# Start all workers
docker compose up -d worker-ingestion worker-clustering worker-analysis

# Start Celery Beat and Flower
docker compose up -d celery-beat flower

# Check all services
docker compose ps
```

### 3. Deploy Frontend from GHCR
```bash
# Disable local build override
mv docker-compose.override.yml docker-compose.override.yml.backup

# Pull CI-built image
docker pull ghcr.io/nicolasgh91/wildfire-recovery-argentina/frontend:latest

# Update docker-compose.yml (manual edit)
# Comment out build section, add:
# image: ghcr.io/nicolasgh91/wildfire-recovery-argentina/frontend:latest

# Start frontend
docker compose up -d frontend

# Start nginx reverse proxy
docker compose up -d nginx
```

### 4. Verification
```bash
# Check all services
docker compose ps

# Test endpoints
curl -f http://localhost:8000/health          # API
curl -s -o /dev/null -w "%{http_code}" http://localhost/  # Frontend
curl -s -o /dev/null -w "%{http_code}" http://localhost:5555/  # Flower

# Check resources
docker stats --no-stream
docker images forestguard-frontend
```

## 🔧 Troubleshooting Commands

### Service Issues
```bash
# Restart specific service
docker compose restart [service-name]

# View logs
docker compose logs [service-name]

# Check service health
docker compose exec [service-name] [command]
```

### Frontend Issues
```bash
# Check frontend container
docker ps | grep frontend
docker logs forestguard-frontend

# Verify image source
docker images forestguard-frontend

# Test frontend directly
docker run --rm -p 8888:80 ghcr.io/nicolasgh91/wildfire-recovery-argentina/frontend:latest
```

### Network Issues
```bash
# Check network connectivity
docker compose exec frontend curl -f http://api:8000/health
docker compose exec api ping redis

# Check networks
docker network ls
docker network inspect wildfire-recovery-argentina_forestguard
```

### Resource Issues
```bash
# Check memory usage
docker stats --no-stream

# Clean up if needed
docker system prune -f
docker compose down
docker compose up -d
```

## 📊 Expected Service Status

```
SERVICE              STATUS      PORTS
redis                Up          6379:6379
api                  Up          8000:8000
worker-ingestion     Up          -
worker-clustering    Up          -
worker-analysis      Up          -
celery-beat          Up          -
flower               Up          5555:5555
frontend             Up          -
nginx                Up          80:80, 443:443
```

## 🎯 Success Indicators

- ✅ All containers show "Up" status
- ✅ API health check returns 200
- ✅ Frontend accessible via http://localhost
- ✅ Flower monitoring accessible on port 5555
- ✅ Frontend memory usage < 64MB
- ✅ Frontend image from GHCR (not local build)

## 🔄 Rollback Commands

If you need to rollback to local build:

```bash
# Stop frontend
docker compose stop frontend

# Restore override file
mv docker-compose.override.yml.backup docker-compose.override.yml

# Restore docker-compose.yml
git checkout docker-compose.yml

# Rebuild locally
docker compose build --no-cache frontend
docker compose up -d frontend
```
