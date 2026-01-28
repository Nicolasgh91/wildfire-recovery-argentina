# 🌲 ForestGuard API

**Plataforma de inteligencia geoespacial para fiscalización legal de incendios forestales en Argentina**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-009688.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14+-blue.svg)](https://www.postgresql.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Production](https://img.shields.io/badge/Production-Live-success.svg)](https://forestguard.freedynamicdns.org/docs)
![Progress](https://img.shields.io/badge/Progress-70%25-green.svg)

> 🌐 **Live Production API**: [https://forestguard.freedynamicdns.org/docs](https://forestguard.freedynamicdns.org/docs)  
> 🖥️ **Infrastructure**: Oracle Cloud Free Tier  
> 📡 **Status**: Active & Monitoring

---

## ✨ Misión

**ForestGuard** es una plataforma de inteligencia ambiental diseñada para **detectar, analizar, auditar y documentar incendios forestales en Argentina**, transformando datos satelitales crudos en **información accionable, trazable y legalmente verificable**.

El proyecto nace para resolver un problema concreto: **los datos sobre incendios existen, pero están fragmentados, son difíciles de interpretar y casi nunca se convierten en evidencia útil para la toma de decisiones, la rendición de cuentas o procesos legales**.

ForestGuard transforma datos satelitales en **evidencia legal** para aplicar el artículo 22 bis de la Ley 26.815, que prohíbe el cambio de uso del suelo en terrenos afectados por incendios durante 30-60 años.

## 🎯 Problema que resuelve

Hoy, en Argentina:

* Los incendios forestales se detectan tarde o se analizan de forma reactiva.
* La información satelital (NASA FIRMS, VIIRS, MODIS) está dispersa y es técnica.
* No existe un sistema unificado que:

  * consolide detecciones en **eventos reales**,
  * permita **auditar zonas específicas**,
  * genere **evidencia verificable** para organismos, ONGs o ciudadanos.

**ForestGuard cierra esa brecha entre datos abiertos y decisiones reales.**

ForestGuard convierte millones de detecciones satelitales en:

* 🔥 **Eventos de incendio** (no solo puntos aislados)
* 🧭 **Auditorías geoespaciales** por radio, parcela o ubicación
* 📜 **Certificados digitales hasheados (PDF)**, verificables públicamente
* 📊 **Historial histórico nacional (2015–presente)**
* 🌱 **Monitoreo de recuperación** de vegetación post-incendio
* 🚧 **Detección de cambios ilegales** de uso del suelo

Todo con una arquitectura moderna, escalable y orientada a APIs.

---

## 🧩 Casos de Uso (11 implementados)

### Core Features

| UC | Nombre | Descripción | Estado |
|----|--------|-------------|--------|
| **UC-01** | Auditoría Anti-Loteo | Verificar restricciones legales por incendios | ✅ DONE |
| **UC-02** | Peritaje Judicial | Generar evidencia forense para causas judiciales | 🔜 PENDING |
| **UC-06** | Reforestación | Monitoreo NDVI de recuperación vegetal (36 meses) | ⏳ IN PROGRESS |
| **UC-07** | Certificación Legal | Emitir certificados digitales verificables | ✅ DONE |
| **UC-08** | Cambio de Uso | Detectar construcción/agricultura ilegal post-fuego | 🔜 PENDING |
| **UC-09** | Denuncias Ciudadanas | Reportes públicos con evidencia satelital | 🔜 PENDING |
| **UC-10** | Calidad del Dato | Métricas de confiabilidad para peritajes | 🔜 PENDING |
| **UC-11** | Reportes Históricos | PDFs de incendios en áreas protegidas | 🔜 PENDING |

### Análisis Avanzado (Próximamente)

| UC | Nombre | Estado |
|----|--------|--------|
| UC-03 | Alertas Tempranas (Drought Index) | 🔜 PENDING |
| UC-04 | Alertas por Capacidad de Respuesta | 🔜 PENDING |
| UC-05 | Tendencias y Proyecciones | 🔜 PENDING |

---

## 🏗️ Arquitectura Unificada

ForestGuard utiliza una **arquitectura híbrida API + Workers** con módulos compartidos para eliminar redundancias:

```text
┌─────────────────────────────────────────────────────────────────┐
│                         USUARIO FINAL                            │
│  (Escribanos, ONGs, Ciudadanos, Fiscales, Investigadores)       │
└────────────────────┬────────────────────────────────────────────┘
                     │ HTTPS
                     ▼
              CLOUDFLARE CDN
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│              FASTAPI APP (Gunicorn + Uvicorn)                    │
│  ✅ UC-01: POST /audit/land-use                                 │
│  ✅ UC-07: POST /certificates/request                           │
│  🔜 UC-02: POST /reports/judicial                               │
│  🔜 UC-11: POST /reports/historical-fire                        │
└────────────────────┬────────────────────────────────────────────┘
                     │
         ┌───────────┴────────────┐
         ▼                        ▼
┌──────────────────┐    ┌──────────────────────┐
│   SUPABASE       │    │   CELERY WORKERS     │
│   PostgreSQL     │    │                      │
│   + PostGIS      │    │  1️⃣ Ingestion        │
│                  │    │  2️⃣ VAE (UC-06, 08)  │
│  📊 14 tables    │    │  3️⃣ Climate          │
└──────────────────┘    └──────────┬───────────┘
                                   │
              ┌────────────────────┴────────────────────┐
              ▼                    ▼                    ▼
      ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
      │ GOOGLE EARTH │    │  NASA FIRMS  │    │  Open-Meteo  │
      │   ENGINE     │    │ (VIIRS/MODIS)│    │  (ERA5-Land) │
      │              │    │              │    │              │
      │ • Sentinel-2 │    │ • Fire spots │    │ • Climate    │
      │ • NDVI       │    │ • 20y history│    │ • Drought    │
      └──────────────┘    └──────────────┘    └──────────────┘
```

### 🆕 Módulos Compartidos (Unified Architecture)

#### Vegetation Analysis Engine (VAE)
Módulo centralizado para análisis de vegetación usando NDVI:
- **UC-06**: Monitoreo de recuperación (reforestación)
- **UC-08**: Detección de cambios ilegales de uso

**Ventajas**: Evita duplicación de procesamiento GEE, mantiene consistencia metodológica.

#### Evidence Reporting Service (ERS)
Motor unificado para generación de reportes verificables:
- **UC-09**: Paquetes de evidencia para denuncias
- **UC-11**: Reportes históricos en áreas protegidas
- **UC-02**: Peritajes judiciales

**Ventajas**: PDFs homogéneos, verificación criptográfica centralizada, auditoría consistente.

---

## 🛠️ Stack Tecnológico

### Backend
| Componente | Tecnología | Versión |
|------------|------------|---------|
| API Framework | FastAPI + Uvicorn | 0.104+ |
| ORM | SQLAlchemy + GeoAlchemy2 | 2.0+ |
| Async Tasks | Celery + Redis | 5.3+ |
| PDF Generation | WeasyPrint | - |

### Database & Storage
| Componente | Tecnología | Límites |
|------------|------------|---------|
| Database | PostgreSQL 14 + PostGIS 3.0 | 500 MB (Supabase free) |
| Object Storage | Cloudflare R2 | 10 GB free |
| Cache/Queue | Redis | - |

### Data Sources
| Fuente | Propósito | Frecuencia |
|--------|-----------|------------|
| NASA FIRMS (VIIRS/MODIS) | Detección de incendios | Diaria |
| Google Earth Engine (GEE) | Imágenes Sentinel-2, NDVI | Mensual |
| Open-Meteo (ERA5-Land) | Datos climáticos históricos | Batch |

### DevOps
| Componente | Tecnología |
|------------|------------|
| Containerization | Docker + Docker Compose |
| CI/CD | GitHub Actions (planned) |
| Deployment | Oracle Cloud / Railway |

---

## 🚀 Quick Start

### Requisitos

- Python 3.11+
- PostgreSQL 14+ con PostGIS
- Redis (para Celery)
- Cuenta en [Supabase](https://supabase.com) (base de datos)
- Cuenta Google Cloud con Earth Engine API habilitada

### Instalación Local

```bash
# 1. Clonar repositorio
git clone https://github.com/Nicolasgh91/wildfire-recovery-argentina.git
cd wildfire-recovery-argentina

# 2. Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Windows: venv\\Scripts\\activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env
# Editar .env con credenciales:
# - Supabase (DB_HOST, DB_PASSWORD)
# - NASA FIRMS API key
# - GEE service account JSON path
# - Cloudflare R2 credentials

# 5. Cargar schema en Supabase
# Ejecutar: database/schema_v0.1.sql en Supabase SQL Editor

# 6. Iniciar servicios (Docker)
docker-compose up -d

# 7. Iniciar API
uvicorn app.main:app --reload --port 8000
```

### Verificar instalación

```bash
# Health check (verifica DB, Redis, GEE, R2)
curl http://localhost:8000/health

# Documentación interactiva OpenAPI
open http://localhost:8000/docs
```

---

## 📚 API Endpoints

### Core Endpoints

#### Auditoría Legal (UC-01) ✅
```bash
POST /api/v1/audit/land-use
```

Verifica si un terreno tiene restricciones por incendios históricos.

**Request:**
```json
{
  "latitude": -27.4658,
  "longitude": -58.8346,
  "radius_meters": 1000
}
```

**Response:**
```json
{
  "fires_found": 2,
  "is_prohibited": true,
  "prohibition_until": "2052-01-31",
  "violation_severity": "medium",
  "legal_summary": "⚠️ TERRENO CON RESTRICCIÓN LEGAL..."
}
```

#### Certificados (UC-07) ✅
```bash
# Solicitar certificado
POST /api/v1/certificates/request

# Descargar PDF
GET /api/v1/certificates/download/{certificate_number}

# Verificar autenticidad (hash SHA-256)
GET /api/v1/certificates/verify/{certificate_number}
```

#### Health Check ✅
```bash
GET https://forestguard.freedynamicdns.org/health
```

Verifica estado de todos los componentes:
- Database (Supabase)
- Redis
- Google Earth Engine
- Cloudflare R2

---

## 📁 Estructura del Proyecto

```
wildfire-recovery-argentina/
├── app/                          # Backend FastAPI
│   ├── api/routes/
│   │   ├── audit.py             # ✅ UC-01
│   │   ├── certificates.py      # ✅ UC-07
│   │   ├── fires.py             # ✅ CRUD
│   │   ├── health.py            # ✅ Health check
│   │   ├── historical.py        # 🔜 UC-11
│   │   ├── reports.py           # 🔜 UC-02
│   │   ├── citizen.py           # 🔜 UC-09
│   │   └── monitoring.py        # 🔜 UC-06
│   ├── services/
│   │   ├── gee_service.py       # ✅ Google Earth Engine
│   │   ├── vae_service.py       # 🔜 Vegetation Analysis Engine
│   │   ├── ers_service.py       # 🔜 Evidence Reporting Service
│   │   ├── spatial_service.py   # ✅ PostGIS queries
│   │   └── pdf_composer.py      # 🔜 PDF generation
│   ├── models/                  # SQLAlchemy ORM
│   ├── schemas/                 # Pydantic validation
│   └── main.py                  # Entry point
├── workers/                      # Celery workers
│   ├── tasks/
│   │   ├── ingestion.py         # ✅ NASA FIRMS
│   │   ├── clustering.py        # ✅ DBSCAN
│   │   ├── recovery.py          # 🔜 VAE: UC-06
│   │   ├── destruction.py       # 🔜 VAE: UC-08
│   │   └── climate.py           # 🔜 Open-Meteo
├── database/
│   ├── schema_v0.1.sql          # ✅ Schema completo (14 tablas)
│   └── supabase.sql             # ✅ RLS policies
├── Architecture/                 # 📖 Documentación
│   ├── forestguard_use_cases.md # ✅ 11 casos de uso
│   ├── forestguard_architecture.md # ✅ Arquitectura técnica
│   └── PROJECT_PLAN.md          # ✅ Roadmap (70% complete)
└── docker/                       # Docker configs
```

---

## 🔧 Configuración

### Variables de Entorno Requeridas

```bash
# Base de datos (Supabase)
DB_HOST=db.xxxx.supabase.co
DB_PORT=5432
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=tu_password_supabase

# Google Earth Engine
GEE_SERVICE_ACCOUNT_JSON=/path/to/gee-service-account.json
# O como variable de entorno (base64)
# GEE_SERVICE_ACCOUNT_JSON=eyJ0eXBlIjoi...

# Cloudflare R2
R2_ACCESS_KEY_ID=tu_access_key
R2_SECRET_ACCESS_KEY=tu_secret_key
R2_ENDPOINT_URL=https://account-id.r2.cloudflarestorage.com
R2_BUCKET_NAME=forestguard-images

# NASA FIRMS
FIRMS_API_KEY=tu_firms_api_key

# Redis
REDIS_URL=redis://localhost:6379/0

# Aplicación
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=tu_clave_secreta_aleatoria
```

### Obtener Credenciales

#### NASA FIRMS API Key
1. Ir a https://firms.modaps.eosdis.nasa.gov/api/area/
2. Registrarse (gratis)
3. Copiar el API key

#### Google Earth Engine
1. Crear proyecto en Google Cloud Console
2. Habilitar Earth Engine API
3. Crear Service Account
4. Descargar JSON key
5. Guardar en `/secrets/gee-service-account.json` (fuera del repo)

#### Cloudflare R2
1. Crear cuenta en Cloudflare
2. Crear bucket R2
3. Generar API token con permisos de lectura/escritura

---

## 🚢 Deploy

### 🌐 Producción (Oracle Cloud Free Tier) ✅

**Status**: LIVE  
**URL**: https://forestguard.freedynamicdns.org  
**API Docs**: https://forestguard.freedynamicdns.org/docs  
**Infrastructure**: Oracle Cloud VM (Always Free)  
**DNS**: FreeDynamicDNS  
**SSL**: Let's Encrypt (Auto-renewal)  

**Deployment Stack**:
- VM Shape: Ampere A1 (ARM) / 1 OCPU, 6GB RAM
- OS: Ubuntu 22.04 LTS
- Reverse Proxy: Nginx
- Process Manager: systemd / PM2
- Database: Supabase (PostgreSQL + PostGIS)
- Storage: Cloudflare R2

### Docker (Desarrollo Local)

```bash
# Desarrollo
docker-compose up -d

# Producción local
docker-compose -f docker-compose.prod.yml up -d
```

### Deploy Manual (Oracle Cloud)

```bash
# 1. Conectar a VM
ssh ubuntu@<instance-ip>

# 2. Clonar repo
git clone https://github.com/Nicolasgh91/wildfire-recovery-argentina.git
cd wildfire-recovery-argentina

# 3. Setup environment
cp .env.example .env
vim .env  # Configurar credenciales

# 4. Instalar dependencias
pip install -r requirements.txt

# 5. Configurar systemd service
sudo cp deployment/forestguard.service /etc/systemd/system/
sudo systemctl enable forestguard
sudo systemctl start forestguard

# 6. Configurar Nginx
sudo cp deployment/nginx.conf /etc/nginx/sites-available/forestguard
sudo ln -s /etc/nginx/sites-available/forestguard /etc/nginx/sites-enabled/
sudo systemctl reload nginx

# 7. SSL con Certbot
sudo certbot --nginx -d forestguard.freedynamicdns.org
```

---

## 📊 Scripts de Mantenimiento

### Carga Incremental de Datos

```bash
# Descargar últimos 2 días de FIRMS
python scripts/load_firms_incremental.py

# Clustering de nuevas detecciones
python workers/tasks/clustering.py --mode incremental

# Enriquecer con datos climáticos
python workers/tasks/climate.py --days 7
```

---

## 📜 Marco Legal

### Ley 26.815 Art. 22 bis

| Tipo de Zona | Prohibición | Aplicable a |
|--------------|-------------|-------------|
| Bosques nativos | **60 años** | Cambio de uso, loteo, construcción |
| Áreas protegidas | **60 años** | Toda actividad extractiva |
| Zonas agrícolas | **30 años** | Cambio de uso productivo |

**Sanciones**: Multas, nulidad de actos, responsabilidad penal por incumplimiento.

---

## 🧪 Testing

```bash
# Ejecutar todos los tests
pytest

# Con coverage (objetivo: >80%)
pytest --cov=app --cov-report=html

# Solo tests de integración
pytest tests/integration/

# E2E de UC-01
pytest tests/e2e/test_audit_flow.py
```

---

## 📈 Roadmap & Estado

### ✅ Completado (70%)

- [x] Schema PostgreSQL v0.2 (14 tablas)
- [x] Casos de uso documentados (11 UCs)
- [x] Arquitectura unificada (VAE + ERS)
- [x] Validación arquitectónica completa
- [x] Carga histórica NASA FIRMS (2015-2025)
- [x] Clustering de eventos (DBSCAN)
- [x] Integración Google Earth Engine
- [x] Endpoints UC-01 (Auditoría)
- [x] Endpoints UC-07 (Certificados)
- [x] Health checks completos
- [x] Docker setup
- [x] Security hardening & RLS policies

### ⏳ En Desarrollo (20%)

- [ ] VAE Service (UC-06, UC-08)
- [ ] ERS Service (UC-09, UC-11)
- [ ] Endpoints faltantes (UC-02, UC-06, UC-09, UC-11)
- [ ] Workers Celery (recovery, destruction)
- [ ] Datos de áreas protegidas

### 🔜 Próximos (10%)

- [ ] Frontend React + Leaflet
- [ ] Tests E2E completos
- [ ] CI/CD (GitHub Actions)
- [ ] Deploy a producción
- [ ] Monitoreo Prometheus

---

## 🔒 Seguridad

### Mejores Prácticas Implementadas

- ✅ **RLS Policies**: Row Level Security en Supabase
- ✅ **Rate Limiting**: 100 req/min por IP (Cloudflare)
- ✅ **GEE Credentials**: Never committed, env variables only
- ✅ **API Versioning**: `/api/v1/` con deprecation policy
- ✅ **Health Checks**: Componente-level monitoring
- ✅ **Error Handling**: Retry policies, DLQ, alerting

### Rate Limits Externos

| Servicio | Límite Free Tier |
|----------|------------------|
| Google Earth Engine | 50,000 requests/day |
| Supabase | 500 MB storage, 60 connections |
| Cloudflare R2 | 10 GB storage, unlimited egress |

---

## 🤝 Contribuir

1. Fork el repositorio
2. Crear branch (`git checkout -b feature/nueva-funcionalidad`)
3. Commit cambios (`git commit -am 'Agregar nueva funcionalidad'`)
4. Push al branch (`git push origin feature/nueva-funcionalidad`)
5. Crear Pull Request

**Áreas que necesitan ayuda**:
- Frontend React (UI/UX)
- Tests E2E
- Documentación de APIs
- Optimización de queries PostGIS

---

## 📄 Licencia

MIT License - Ver [LICENSE](LICENSE) para detalles.

---

## 👨‍💻 Autor

**Nicolás Gabriel Hruszczak**  
Business Analyst / Full-Stack Developer

📧 Email: nicolasgh91@gmail.com  
🔗 GitHub: [@Nicolasgh91](https://github.com/Nicolasgh91)  
💼 LinkedIn: [Nicolas Hruszczak](https://www.linkedin.com/in/nicolas-hruszczak/)

---

## 🙏 Agradecimientos

- **NASA FIRMS** - Datos abiertos de detección de incendios
- **Google Earth Engine** - Procesamiento satelital server-side
- **Supabase** - Base de datos PostgreSQL + PostGIS
- **FastAPI** - Framework web moderno
- **Cloudflare** - CDN y object storage (R2)

---

## 🌍 Por qué ForestGuard importa

Los incendios forestales ya no son eventos aislados: son **riesgo sistémico**. La transparencia ambiental es clave para políticas públicas efectivas. Los datos abiertos solo generan impacto cuando se transforman en **evidencia accionable**.

**ForestGuard convierte datos en decisiones, y decisiones en responsabilidad.**

---

**Última actualización:** Enero 2026  
**Versión:** 2.0.0  
**Progreso:** 70% completado

[![Star on GitHub](https://img.shields.io/github/stars/Nicolasgh91/wildfire-recovery-argentina?style=social)](https://github.com/Nicolasgh91/wildfire-recovery-argentina)
