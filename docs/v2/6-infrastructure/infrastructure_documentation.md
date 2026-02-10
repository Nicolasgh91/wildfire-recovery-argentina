# ForestGuard - Infraestructura y Deployment v2.0

**Fecha de actualización**: Febrero 2026  
**Entorno de producción**: Oracle Cloud Always Free  
**Estado**: Desplegado y en producción  
**URL**: `https://forestguard.app`

---

## 1. Visión General de Infraestructura

ForestGuard utiliza una estrategia **"Cost Zero"** aprovechando tiers gratuitos de múltiples proveedores cloud, optimizando para:

1. **Costo $0/mes** en condiciones normales (< 100 usuarios)
2. **Escalabilidad horizontal** cuando sea necesario
3. **Alta disponibilidad** dentro de límites de free tier
4. **Seguridad por defecto** (RLS, HTTPS, secrets management)

### 1.1 Arquitectura Cloud

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        FORESTGUARD CLOUD ARCHITECTURE                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                           INTERNET USERS                              │   │
│  │               (Browsers, Mobile Devices, API Clients)                 │   │
│  └───────────────────────────────┬──────────────────────────────────────┘   │
│                                  │                                          │
│                                  ▼                                          │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                        CLOUDFLARE (Free CDN)                           │  │
│  │  • DNS Management           • DDoS Protection                          │  │
│  │  • SSL/TLS Termination      • Global CDN                               │  │
│  │  • Cache for static assets  • Web Application Firewall                 │  │
│  └───────────────────────────────┬───────────────────────────────────────┘  │
│                                  │                                          │
│                   ┌──────────────┴──────────────┐                           │
│                   ▼                             ▼                           │
│  ┌─────────────────────────────┐  ┌─────────────────────────────────────┐   │
│  │   ORACLE CLOUD (FREE TIER)  │  │  VERCEL / NETLIFY (Frontend CDN)    │   │
│  │   Ampere A1 Compute         │  │  • React SPA Hosting (Free)         │   │
│  │   • 1 vCPUs ARM64           │  │  • Automatic HTTPS                  │   │
│  │   • 1 GB RAM                │  │  • Edge network caching             │   │
│  │   • 100 GB Storage          │  │  • GitHub integration               │   │
│  │   • Oracle Linux 8          │  └─────────────────────────────────────┘   │
│  │                             │                                            │
│  │   ┌───────────────────────┐ │                                            │
│  │   │ NGINX (Reverse Proxy) │ │                                            │
│  │   │   • SSL Termination   │ │                                            │
│  │   │   • Rate Limiting     │ │                                            │
│  │   │   • Gzip Compression  │ │                                            │
│  │   └──────────┬────────────┘ │                                            │
│  │              │              │                                            │
│  │   ┌──────────▼───────────┐  │                                            │
│  │   │ BACKEND API (FastAPI)│  │                                            │
│  │   │  • Uvicorn (ASGI)    │  │                                            │
│  │   │  • Systemd service   │  │                                            │
│  │   │  • Port 8000         │  │                                            │
│  │   └──────────┬───────────┘  │                                            │
│  │              │              │                                            │
│  │   ┌──────────▼───────────┐  │                                            │
│  │   │  CELERY WORKERS      │  │                                            │
│  │   │  • Episode clustering│  │                                            │
│  │   │  • Carousel images   │  │                                            │
│  │   │  • Closure reports   │  │                                            │
│  │   │  • NASA FIRMS sync   │  │                                            │
│  │   └──────────┬───────────┘  │                                            │
│  │              │              │                                            │
│  │   ┌──────────▼───────────┐  │                                            │
│  │   │   REDIS 7.x          │  │                                            │
│  │   │   • Message broker   │  │                                            │
│  │   │   • Result backend   │  │                                            │
│  │   │   • AOF persistence  │  │                                            │
│  │   └──────────────────────┘  │                                            │
│  └─────────────────────────────┘                                            │
│                   │                                                          │
│                   └────────────────┬─────────────────────┐                   │
│                                    ▼                     ▼                   │
│  ┌─────────────────────────────────────────┐  ┌──────────────────────────┐  │
│  │  SUPABASE (Free Tier)                   │  │  GOOGLE CLOUD PLATFORM   │  │
│  │  • PostgreSQL 15 + PostGIS 3.3          │  │  • Cloud Storage (GCS)   │  │
│  │  • 500 MB Database (30+ tables)         │  │  • 5 GB free tier        │  │
│  │  • Supabase Auth (Google OAuth + Email) │  │  • Satellite thumbnails  │  │
│  │  • Row Level Security (RLS)             │  │  • Service account key   │  │
│  │  • Automatic backups                    │  │                          │  │
│  │  • Edge Functions (public-stats)        │  │  • Earth Engine (GEE)    │  │
│  └─────────────────────────────────────────┘  │  • 50k requests/day      │  │
│                                                │  • Sentinel-2 imagery    │  │
│                                                └──────────────────────────┘  │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                        EXTERNAL APIS (FREE TIERS)                      │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                 │  │
│  │  │ NASA FIRMS   │  │ Open-Meteo   │  │ MercadoPago  │                 │  │
│  │  │ VIIRS/MODIS  │  │ Climate API  │  │ Payment API  │                 │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘                 │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Proveedores Cloud y Servicios

### 2.1 Oracle Cloud Infrastructure (OCI) - Always Free Tier

**Recurso principal**: Ampere A1 Compute (ARM64)

| Recurso | Especificación | Uso en ForestGuard |
|---------|----------------|-------------------|
| **vCPUs** | 1 OCPUs ARM64 | Backend API + Celery workers + Redis |
| **RAM** | 1 GB 
| **Storage** | 100 GB Block Volume
| **Bandwidth** | 10 TB/mes | Tráfico API + frontend (estimado ~500 GB/mes) |
| **IP Pública** | 1 IPv4 estática | `https://forestguard.freedynamicdns.org/` |
| **Firewall** | Security Lists | HTTPS (443), SSH (22), API (8000 interno) |

**Sistema Operativo**: Oracle Linux 8

**Servicios corriendo**:
```bash
systemctl list-units | grep forestguard
forestguard-backend.service    # FastAPI + Uvicorn
forestguard-celery.service     # Celery worker
forestguard-beat.service       # Celery beat scheduler
redis-server.service           # Redis 7.x
nginx.service                  # Reverse proxy
```

---

### 2.2 Supabase - PostgreSQL + Auth

**Plan**: Free Tier

| Característica | Límite | Uso actual |
|----------------|--------|------------|
| **Database Size** | 500 MB | ~280 MB (56%) |
| **Egress** | Unlimited | API queries |
| **Database Rows** | Unlimited | ~150k fire detections |
| **Auth Users** | 50,000 | ~20 usuarios activos |
| **Storage** | 1 GB | No usado (imágenes en GCS) |
| **Edge Functions** | 500k invocations/month | `public-stats` (~5k/month) |

**Extensiones habilitadas**:
- `postgis` 3.3.x - Operaciones geoespaciales
- `h3` 4.1.x - H3 spatial indexing
- `pg_stat_statements` - Query monitoring
- `uuid-ossp` - UUID generation

**Backup Strategy**:
- **Automático**: Daily snapshots (retención 7 días)
- **Manual**: Export a Parquet para archivado (cada 90 días)

**Connection Pooling**:
```python
# app/core/database.py
DATABASE_URL = (
    f"postgresql+asyncpg://{USER}:{PASS}@{HOST}:5432/{DB}"
    "?prepared_statement_cache_size=0"
)
engine = create_async_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)
```

---

### 2.3 Google Cloud Platform

#### 2.3.1 Cloud Storage (GCS)

**Bucket**: `images`  
**Región**: `us-central1` (Iowa, USA)  
**Storage Class**: Standard

| Recurso | Límite Free | Uso actual |
|---------|-------------|------------|
| **Storage** | 5 GB | ~2.3 GB (46%) |
| **Class A ops** | 5,000/month | ~1,200 (uploads) |
| **Class B ops** | 50,000/month | ~8,500 (downloads) |
| **Egress** | 1 GB/month (Worldwide) | ~800 MB |

**Estructura de almacenamiento**:
```
gs://images/
├── fires/
│   └── {fire_event_id}/
│       └── thumbnails/
│           ├── {date}_sentinel2_rgb.webp
│           └── {date}_sentinel2_ndvi.webp
├── episodes/
│   └── {episode_id}/
│       ├── closure_report/
│       │   ├── pre_fire.webp
│       │   └── post_fire.webp
│       └── carousel/
│           └── {timestamp}.webp
└── reports/
    └── {report_id}/
        └── {report_hash}.pdf
```

**Lifecycle Policy**:
```json
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "SetStorageClass", "storageClass": "NEARLINE"},
        "condition": {"age": 90, "matchesPrefix": ["reports/"]}
      },
      {
        "action": {"type": "Delete"},
        "condition": {"age": 365, "matchesPrefix": ["fires/"]}
      }
    ]
  }
}
```

#### 2.3.2 Earth Engine (GEE)

**Account Type**: No-commercial use (Free)

| Cuota | Límite | Uso típico |
|-------|--------|------------|
| **Requests** | 50,000/day | ~1,200/day (30 fires × 40 images) |
| **Assets** | 250 GB | 0 GB (no almacenamos en GEE) |
| **Compute** | Limited concurrent | 5 concurrent max |

**Service Account**:
```
[EMAIL_ADDRESS]
```

**Credenciales**:
```bash
# Ubicación: secrets/gee-service-account.json (git-ignored)
GOOGLE_APPLICATION_CREDENTIALS=path

---

### 2.4 Cloudflare - CDN y DNS

**Plan**: Free

| Feature | Configuración |
|---------|--------------|
| **DNS** | `forestguard.app` + `www` |
| **SSL** | Full (strict) - Let's Encrypt + Origin cert |
| **Caching** | Aggressive for static assets |
| **Security Level** | Medium |
| **Always Use HTTPS** | ✅ Enabled |
| **Auto Minify** | CSS, JS, HTML |

**Page Rules**:
```
1. forestguard.app/api/*
   - Cache Level: Bypass
   - Security Level: Medium

2. forestguard.app/static/*
   - Cache Level: Cache Everything
   - Edge Cache TTL: 1 month
   - Browser Cache TTL: 1 week

3. www.forestguard.app/*
   - Forwarding URL: 301 to https://forestguard.app$1
```

---

### 2.5 Vercel / Netlify - Frontend Hosting (Opcional)

**Plan**: Free (Hobby)

Si se despliega el frontend por separado (actualmente servido desde Oracle Cloud):

| Feature | Vercel | Netlify |
|---------|--------|---------|
| **Build minutes** | 6,000/month | 300/month |
| **Bandwidth** | 100 GB/month | 100 GB/month |
| **Deployments** | Unlimited | Unlimited |
| **Custom domain** | ✅ | ✅ |
| **Automatic HTTPS** | ✅ | ✅ |
| **GitHub integration** | ✅ | ✅ |

**Configuración de build** (Vercel):
```json
// vercel.json
{
  "framework": "vite",
  "buildCommand": "npm run build",
  "outputDirectory": "dist",
  "installCommand": "npm ci",
  "env": {
    "VITE_API_BASE_URL": "https://forestguard.app",
    "VITE_SUPABASE_URL": "@supabase_url",
    "VITE_SUPABASE_ANON_KEY": "@supabase_anon_key"
  }
}
```

---

## 3. Deployment y CI/CD

### 3.1 Infraestructura como Código (IaC)

**Archivos de configuración**:

```bash
infrastructure/
├── nginx/
│   ├── forestguard.conf          # Reverse proxy config
│   └── ssl/
│       ├── fullchain.pem         # Let's Encrypt cert
│       └── privkey.pem           # Private key
├── systemd/
│   ├── forestguard-backend.service
│   ├── forestguard-celery.service
│   └── forestguard-beat.service
├── docker-compose.yml            # Development environment
├── Dockerfile                    # Backend image (future)
└── terraform/                    # OCI provisioning (future)
    └── main.tf
```

---

### 3.2 Deployment Process

#### 3.2.1 Backend Deployment

**Método actual**: Manual via SSH + systemd

```bash
# 1. SSH into Oracle Cloud instance
ssh ubuntu@forestguard.app

# 2. Pull latest code
cd /opt/forestguard
git pull origin main

# 3. Install/update dependencies
source venv/bin/activate
pip install -r requirements.txt --upgrade

# 4. Run database migrations
alembic upgrade head

# 5. Restart services
sudo systemctl restart forestguard-backend
sudo systemctl restart forestguard-celery
sudo systemctl restart forestguard-beat

# 6. Verify status
sudo systemctl status forestguard-backend
curl https://forestguard.app/health/ready
```

**Rollback**:
```bash
# Revert to previous commit
git reset --hard HEAD~1

# Downgrade migrations if needed
alembic downgrade -1

# Restart services
sudo systemctl restart forestguard-backend
```

---

#### 3.2.2 Frontend Deployment

**Método A: Servido desde Oracle Cloud (actual)**

```bash
# En servidor Oracle Cloud
cd /opt/forestguard/frontend
npm ci
npm run build

# Nginx sirve desde /opt/forestguard/frontend/dist
sudo systemctl reload nginx
```

**Método B: Vercel (recomendado para staging)**

```bash
# Push to GitHub triggers automatic deployment
git push origin staging
# Vercel auto-builds and deploys to staging.forestguard.app
```

---

### 3.3 CI/CD Pipeline (GitHub Actions)

**Archivo**: `.github/workflows/ci.yml`

```yaml
name: CI Pipeline

on:
  push:
    branches: [main, staging, develop]
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install ruff mypy
      - run: ruff check app/
      - run: mypy app/ --ignore-missing-imports

  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install -r requirements.txt pytest-cov
      - run: pytest tests/ --cov=app --cov-fail-under=60 -v

  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install pip-audit
      - run: pip-audit --strict
      - run: cd frontend && npm audit --audit-level=high

  deploy-staging:
    needs: [lint, test, security]
    if: github.ref == 'refs/heads/staging'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Deploy to staging
        run: |
          # Trigger deployment hook (future: webhook to Oracle Cloud)
          echo "Deploy to staging"
```

---

### 3.4 Secrets Management

**Variables de entorno sensibles**:

```bash
# Ubicación: /opt/forestguard/.env (no versionado)
DATABASE_URL=postgresql://...
SECRET_KEY=<random_256bit>
SUPABASE_URL=https://...
SUPABASE_SERVICE_KEY=<service_role_key>
GOOGLE_APPLICATION_CREDENTIALS=path
GCS_BUCKET_NAME=images
MERCADOPAGO_ACCESS_TOKEN=<access_token>
SMTP_PASSWORD=<app_password>
```

**Rotación de secrets**:
- `SECRET_KEY`: Anual (genera nuevos JWT)
- `SUPABASE_SERVICE_KEY`: No rotar (rompe integración)
- `GEE Service Account`: Cada 90 días (buena práctica)
- `MERCADOPAGO_ACCESS_TOKEN`: Al cambiar de account

---

## 4. Monitoreo y Observabilidad

### 4.1 Health Checks

**Endpoints**:

| Endpoint | Propósito | Intervalo de verificación |
|----------|-----------|---------------------------|
| `GET /health` | Liveness probe (¿responde el proceso?) | 30s |
| `GET /health/ready` | Readiness probe (¿dependencias ok?) | 60s |
| `GET /metrics` | Métricas Prometheus (internal) | On-demand |

**Verificación externa**:
```bash
# UptimeRobot (free tier - 50 monitors)
https://uptimerobot.com
  - Monitor 1: https://forestguard.app/health (HTTP 200)
  - Monitor 2: https://forestguard.app/api/v1/fires/stats (JSON response)
  - Alert: Email si down > 5 min
```

---

### 4.2 Logging

**Stack**: Structured JSON logging

```python
# app/core/logging.py
import structlog

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
)

logger = structlog.get_logger()
logger.info("fire_event_created", fire_id=str(event.id), province=event.province)
```

**Almacenamiento**:
```bash
# Logs en Oracle Cloud
/var/log/forestguard/
├── backend.log          # FastAPI logs
├── celery-worker.log    # Worker logs
├── celery-beat.log      # Scheduler logs
├── nginx-access.log     # HTTP access logs
└── nginx-error.log      # Nginx errors

# Rotación con logrotate
/etc/logrotate.d/forestguard
  - Daily rotation
  - Compress after 1 day
  - Keep 30 days
  - Max size 100M per log
```

---

### 4.3 Métricas (Prometheus + Grafana - Futuro)

**Stack propuesto**:

| Componente | Propósito | Hosting |
|------------|-----------|---------|
| **Prometheus** | Metrics storage | Oracle Cloud (puerto 9090) |
| **Grafana** | Dashboards | Oracle Cloud (puerto 3000) |
| **Node Exporter** | System metrics | Oracle Cloud |
| **Postgres Exporter** | Database metrics | Supabase (si soporta) |

**Métricas clave**:

```
# Application metrics
http_requests_total{method, endpoint, status}
http_request_duration_seconds{method, endpoint}
celery_tasks_total{task_name, state}
celery_task_duration_seconds{task_name}

# System metrics
node_cpu_seconds_total
node_memory_MemAvailable_bytes
node_disk_io_time_seconds_total

# Database metrics
pg_stat_database_numbackends
pg_database_size_bytes{datname="postgres"}
pg_stat_user_tables_n_tup_ins{relname}
```

**Dashboards**:
1. **Overview**: Requests/s, latency p95, error rate, CPU/RAM
2. **API Endpoints**: Top 10 slowest, highest error rate
3. **Celery Workers**: Tasks queued, completed, failed
4. **Database**: Connection pool, query performance, disk usage

---

### 4.4 Alertas

**UptimeRobot (free)**:
- API downtime > 5 min → Email
- Response time > 10s → Email

**Grafana Alerts (futuro)**:
```yaml
alerts:
  - name: HighErrorRate
    condition: rate(http_requests_total{status=~"5.."}[5m]) > 10
    severity: critical
    notification: email

  - name: DatabaseSizeWarning
    condition: pg_database_size_bytes > 450MB
    severity: warning
    notification: email

  - name: CeleryQueueBacklog
    condition: celery_queue_length > 100
    severity: warning
    notification: slack
```

---

## 5. Seguridad de Infraestructura

### 5.1 Network Security

**Oracle Cloud Security Lists**:

| Puerto | Protocolo | Source | Propósito |
|--------|-----------|--------|-----------|
| 22 | TCP | Admin IP only | SSH access |
| 80 | TCP | 0.0.0.0/0 | HTTP (redirect to 443) |
| 443 | TCP | 0.0.0.0/0 | HTTPS |
| 8000 | TCP | 127.0.0.1 | Backend API (interno) |
| 6379 | TCP | 127.0.0.1 | Redis (interno) |

**Firewall (ufw)**:
```bash
sudo ufw status
Status: active

To                         Action      From
--                         ------      ----
22/tcp                     LIMIT       Anywhere
80/tcp                     ALLOW       Anywhere
443/tcp                    ALLOW       Anywhere
```

---

### 5.2 SSL/TLS Configuration

**Nginx SSL Config**:
```nginx
# /etc/nginx/sites-available/forestguard.conf
server {
    listen 443 ssl http2;
    server_name forestguard.app;

    ssl_certificate /etc/letsencrypt/live/forestguard.app/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/forestguard.app/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256';
    ssl_prefer_server_ciphers off;

    # HSTS
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Security headers
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
}
```

**Certificate Renewal** (Let's Encrypt):
```bash
# Certbot auto-renewal (cron)
0 0 1 * * certbot renew --quiet && systemctl reload nginx
```

---

### 5.3 Hardening Checklist

```
SISTEMA OPERATIVO
  ☑ Automatic security updates enabled (unattended-upgrades)
  ☑ SSH key-only authentication (password auth disabled)
  ☑ Fail2ban configured (5 failed SSH attempts = 10 min ban)
  ☑ Non-root user for application
  ☑ AppArmor enabled

APLICACIÓN
  ☑ Secrets en .env (no versionado)
  ☑ GEE credentials en secrets/ (git-ignored)
  ☑ CORS configurado por ambiente
  ☑ Rate limiting en Nginx (10 req/s por IP)
  ☑ Security headers configured

BASE DE DATOS
  ☑ RLS habilitado en todas las tablas
  ☑ Connection pooling configurado
  ☑ Strong password (30+ caracteres aleatorios)
  ☑ Backup automático diario

SERVICIOS EXTERNOS
  ☑ API keys rotadas trimestralmente
  ☑ GCS bucket no público (IAM policies)
  ☑ MercadoPago webhooks con signature verification
```

---

## 6. Estrategia FinOps (Cost Zero)

### 6.1 Métricas de Costos Actuales

| Servicio | Plan | Costo mensual | Límite crítico |
|----------|------|---------------|----------------|
| **Oracle Cloud** | Always Free | $0 | 1 OCPUs, 1 GB RAM |
| **Supabase** | Free | $0 | 500 MB database |
| **Google Cloud** | Free Tier | $0 | 5 GB storage, 50k GEE req/day |
| **Cloudflare** | Free | $0 | Bandwidth ilimitado |
| **Vercel** | Hobby | $0 | 100 GB bandwidth/month |
| **UptimeRobot** | Free | $0 | 50 monitors |
| **GitHub** | Free | $0 | Public repo |
| **Total** | — | **$0/mes** | — |

---

### 6.2 Triggers para Escalar (Costos > $0)

| Métrica | Límite Free | Siguiente tier | Costo estimado |
|---------|-------------|----------------|----------------|
| **Supabase DB** | 500 MB | Pro: 8 GB | $25/mes |
| **GCS Storage** | 5 GB | Standard pricing | ~$0.02/GB/mes = $0.20 por 10 GB |
| **GEE Requests** | 50k/day | Commercial tier | Contactar Google |
| **Oracle CPU** | 4 OCPUs | Paid shape | ~$0.01/OCPU-hour = $30/mes por +4 OCPUs |

**Proyección de costos por usuarios**:

```
< 100 usuarios/mes:    $0/mes (free tier)
100-500 usuarios:      $0-25/mes (solo Supabase Pro si DB > 500MB)
500-1000 usuarios:     $25-50/mes (+ GCS storage)
> 1000 usuarios:       $50-150/mes (+ Oracle compute upgrade)
```

---

### 6.3 Optimizaciones para Mantenerse en Free Tier

**Database (500 MB limit)**:

1. **Archivado a Parquet**: Mover fire_detections > 90 días a GCS
```python
# Cronjob mensual
SELECT * FROM fire_detections WHERE detection_date < NOW() - INTERVAL '90 days'
  INTO OUTFILE 's3://forestguard-archive/detections_YYYY-MM.parquet'
```

2. **Compresión de JSONB**: Usar `pg_column_size()` para auditar
3. **Cleanup de thumbnails**: Retention de 365 días

**GCS Storage (5 GB limit)**:

1. **WebP compression**: Todas las imágenes en WebP (50% menos espacio que PNG)
2. **Lifecycle policy**: Nearline después de 90 días, Delete después de 365 días
3. **On-demand HD**: No persistir imágenes HD (generar solo cuando se solicitan)

**GEE Quota (50k req/day)**:

1. **Batch processing**: 15 fires por corrida diaria
2. **Priorización**: Solo incendios > 10 ha en áreas protegidas
3. **Cloud threshold adaptativo**: 10% → 20% → 30% para reducir reintentos

---

## 7. Disaster Recovery y Backups

### 7.1 Backup Strategy

| Componente | Frecuencia | Retención | Ubicación |
|------------|-----------|-----------|-----------|
| **Supabase Database** | Diaria (automática) | 7 días | Supabase backup |
| **Manual DB Export** | Mensual | 12 meses | GCS `gs://forestguard-backups/` |
| **GCS Thumbnails** | No backup (reproducible) | — | Regenerable desde GEE |
| **Application Code** | Cada push | Infinito | GitHub |
| **Secrets** | Manual (encrypted) | Infinito | Secure note manager |

---

### 7.2 Recovery Procedures

**Escenario 1: Database corruption**

```bash
# Restaurar desde backup automático de Supabase
# Via dashboard: Settings → Backups → Restore

# O desde export manual
pg_restore -h <host> -U postgres -d postgres backup_YYYY-MM-DD.dump
```

**Escenario 2: Oracle Cloud instance destroyed**

```bash
# 1. Provisionar nueva instancia (Always Free Ampere A1)
# 2. Configurar security lists (puertos 22, 80, 443)
# 3. Clonar repositorio
git clone https://github.com/user/forestguard.git /opt/forestguard

# 4. Restaurar secrets
# Copiar manualmente .env y secrets/ desde backup seguro

# 5. Instalar dependencias
cd /opt/forestguard
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 6. Configurar systemd services
sudo cp infrastructure/systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now forestguard-backend

# 7. Configurar Nginx
sudo cp infrastructure/nginx/forestguard.conf /etc/nginx/sites-available/
sudo ln -s /etc/nginx/sites-available/forestguard.conf /etc/nginx/sites-enabled/
sudo systemctl restart nginx

# 8. Renovar SSL cert
sudo certbot --nginx -d forestguard.app
```

**RTO/RPO**:
- **RTO** (Recovery Time Objective): 4 horas
- **RPO** (Recovery Point Objective): 24 horas (último backup diario)

---

## 8. Roadmap de Infraestructura

### Corto Plazo (1-3 meses)

- [ ] Implementar Prometheus + Grafana para métricas
- [ ] Configurar alertas automáticas (email + Slack)
- [ ] Terraform para IaC de Oracle Cloud
- [ ] CI/CD completo con GitHub Actions (deploy automático a staging)

### Medio Plazo (3-6 meses)

- [ ] Migrar frontend a Vercel/Netlify
- [ ] CDN para thumbnails (Cloudflare R2)
- [ ] Load testing con k6
- [ ] Disaster recovery drill (quarterly)

### Largo Plazo (6-12 meses)

- [ ] Multi-region deployment (si > 1000 usuarios)
- [ ] Kubernetes migration (si necesita auto-scaling)
- [ ] Managed PostgreSQL (si DB > 500 MB consistently)
- [ ] Professional GEE account (si > 50k req/day)

---

**Documento actualizado**: Febrero 2026  
**Próxima revisión**: Post-implementación de Prometheus/Grafana  
**Mantenedor**: DevOps Lead  
**Estado**: 🟢 Producción estable
