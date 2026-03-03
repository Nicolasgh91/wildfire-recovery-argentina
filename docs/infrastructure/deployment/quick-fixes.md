# Quick Fixes for Common Issues

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

## 🚨 Most Common Problems & Solutions

### 1. Website Down - Quick Diagnosis
```bash
# Run the full analysis script first
./vm-analysis-script.sh

# Quick status check
docker compose ps
curl -I http://localhost/
curl -I https://forestguard.freedynamicdns.org/
```

### 2. Nginx Issues (Most Likely Cause)
```bash
# Check if nginx is running before exec
docker compose ps --status running --services | grep -q '^nginx$' \
  && docker compose exec -T nginx nginx -t \
  || (echo "nginx is not running" && docker compose logs nginx --tail=100)

# View nginx logs
docker compose logs nginx

# Restart nginx
docker compose restart nginx

# If config error, check nginx.conf file
cat nginx.conf
```

### 3. Frontend Container Issues
```bash
# Check frontend status
docker compose ps frontend

# View frontend logs
docker compose logs frontend

# Restart frontend
docker compose restart frontend

# If using GHCR image, verify it's pulled
docker images | grep frontend

# Manually pull latest image
docker pull ghcr.io/nicolasgh91/wildfire-recovery-argentina/frontend:latest
```

### 3.1 Blank Page After "Successful" Deploy
```bash
# Validate frontend build-time vars required by Vite bundle
grep -E '^VITE_(API_BASE_URL|SUPABASE_URL|SUPABASE_ANON_KEY|API_KEY|USE_SUPABASE_JWT|SENTRY_DSN|AUTH_REDIRECT_URL)=' .env

# Optional: hotfix file inside frontend build context
cp frontend/.env.production.example frontend/.env.production
# then edit frontend/.env.production with production values

# Production guardrail: API base URL must not be localhost
grep -E '^VITE_API_BASE_URL=' .env

# Rebuild frontend only (new deploy.sh support)
./scripts/deploy.sh --build frontend

# Validate resulting containers and logs
docker compose ps frontend nginx
docker compose logs frontend --tail=120
docker compose logs nginx --tail=120
```

Expected:
- `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` are present
- `VITE_API_BASE_URL` uses `/api/v1` (or external non-localhost URL)
- `frontend` and `nginx` are running after rebuild

### 4. API Backend Issues
```bash
# Test API health
curl -f http://localhost:8000/health

# Check API logs
docker compose logs api
docker compose logs api --tail=200

# Verify health from inside the API container (useful for unhealthy status triage)
docker compose exec -T api curl -f http://localhost:8000/health

# Restart API
docker compose restart api

# Check Redis connectivity
docker compose exec api python -c "import redis; r=redis.Redis(host='redis'); print(r.ping())"
```

### 5. SSL Certificate Issues
```bash
# Check certificate files
ls -la ./certbot/conf/
find ./certbot/conf -name "*.crt"

# Check certificate expiry
openssl x509 -in ./certbot/conf/live/forestguard.freedynamicdns.org/fullchain.pem -text -noout | grep "Not After"

# Renew certificates (if needed)
docker compose --profile ssl run --rm certbot renew --webroot --webroot-path=/var/www/certbot

# Reload nginx after renewal
docker compose exec -T nginx nginx -s reload || docker compose restart nginx
```

### 6. Port/Firewall Issues
```bash
# Check listening ports
netstat -tlnp | grep -E ':(80|443)'

# Check firewall rules
sudo iptables -L -n | head -20

# Open ports if needed (Oracle Cloud specific)
# This may need to be done in Oracle Cloud Console
```

### 7. Memory Issues (1GB VM)
```bash
# Check memory usage
free -h
docker stats --no-stream

# If memory exhausted, add swap
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Restart services with proper limits
docker compose down
docker compose up -d
```

## 🔄 Complete Restart Procedure

### Full Service Restart
```bash
# Stop all services
docker compose down

# Wait 10 seconds
sleep 10

# Start all services
docker compose up -d

# Check status
docker compose ps

# Wait for services to be ready
sleep 30

# Test website
curl -I https://forestguard.freedynamicdns.org/
```

### Selective Restart
```bash
# Restart just frontend and nginx
docker compose restart frontend nginx

# Or restart backend services
docker compose restart api redis
docker compose restart worker-fast worker-gee
docker compose restart celery-beat flower
```

## 📊 Service Dependencies

```
Start Order:
1. Redis (must be first)
2. API (depends on Redis)
3. Workers (depend on Redis)
4. Celery Beat (depends on Redis)
5. Flower (depends on Redis)
6. Frontend (depends on API)
7. Nginx (depends on Frontend + API)
```

## 🚨 Emergency Procedures

### Website Completely Down
```bash
# 1. Quick diagnosis
docker compose ps
curl -I http://localhost/

# 2. If nginx is down
docker compose restart nginx

# 3. If frontend is down
docker compose restart frontend

# 4. If backend is down
docker compose restart api redis

# 5. Full restart if needed
docker compose down && docker compose up -d
```

### High Memory Usage
```bash
# Check what's using memory
docker stats --no-stream

# Add swap if needed
sudo swapon --show
free -h

# Clean up Docker
docker system prune -f

# Restart with limits
docker compose down
docker compose up -d
```

### SSL Certificate Expired
```bash
# Check cert status
openssl x509 -in ./certbot/conf/live/forestguard.freedynamicdns.org/fullchain.pem -noout -dates

# Renew certificates
docker compose --profile ssl run --rm certbot renew --webroot --webroot-path=/var/www/certbot

# Reload nginx after renewal
docker compose exec -T nginx nginx -s reload || docker compose restart nginx
```

## 📱 Testing After Fixes

Always test after making changes:

```bash
# Test locally
curl -I http://localhost/
curl -I http://localhost:8000/health

# Test externally
curl -I https://forestguard.freedynamicdns.org/

# Check all services
docker compose ps

# Monitor logs
docker compose logs -f --tail=10
```

## 🆘 When to Ask for Help

Contact support if:
- Multiple services won't start
- Persistent SSL certificate issues
- Memory exhaustion despite cleanup
- Network connectivity problems
- Unknown errors in logs

Always provide:
- Output of `docker compose ps`
- Relevant error logs
- What you've already tried
- How long the issue has been occurring
