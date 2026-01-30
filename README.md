# 🌲 ForestGuard API

**Plataforma de inteligencia geoespacial para fiscalización legal de incendios forestales en Argentina**

> 🌍 **Read in english**: [Jump to english version](#-forestguard-api-english-version)


[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-009688.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14+-blue.svg)](https://www.postgresql.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Production](https://img.shields.io/badge/Production-Live-success.svg)](https://forestguard.freedynamicdns.org/docs)
![Progress](https://img.shields.io/badge/Progress-70%25-green.svg)

> 🌐 **Live production API**: [https://forestguard.freedynamicdns.org/docs](https://forestguard.freedynamicdns.org/docs)  
> 🖥️ **Infrastructure**: Oracle Cloud free tier  
> 📡 **Status**: Active & Monitoring

---

## ✨ Misión

**ForestGuard** es una plataforma de inteligencia ambiental diseñada para **detectar, analizar, auditar y documentar incendios forestales en Argentina**, transformando datos satelitales crudos en **información accionable, trazable y legalmente verificable**.

El proyecto nace para resolver un problema concreto: **los datos sobre incendios existen, pero están fragmentados, son difíciles de interpretar y casi nunca se convierten en evidencia útil para la toma de decisiones o procesos legales**.

ForestGuard transforma datos satelitales en **evidencia legal** para aplicar el artículo 22 bis de la Ley 26.815, que prohíbe el cambio de uso del suelo en terrenos afectados por incendios durante 30-60 años.

## 🎯 Problema que resuelve

Hoy, en Argentina:

* Los incendios forestales se detectan tarde o se analizan de forma reactiva.
* La información satelital (NASA FIRMS, VIIRS, MODIS) está dispersa y es técnica.
* No existe un sistema unificado que:

  * consolide detecciones en **eventos reales**,
  * permita **auditar zonas específicas**,
  * genere **evidencia verificable** para organismos, ONGs o personas interesadas.

**ForestGuard cierra esa brecha entre datos abiertos y decisiones reales.**

ForestGuard convierte millones de detecciones satelitales en:

* 🔥 **Eventos de incendio** (no solo puntos aislados)
* 🧭 **Auditorías geoespaciales** por radio, parcela o ubicación
* 📜 **Certificados digitales hasheados (PDF)**, verificables públicamente
* 📊 **Historial histórico nacional (2015–presente)**
* 🌱 **Monitoreo de recuperación** de vegetación post-incendio
* 🚧 **Detección de cambios ilegales** de uso del suelo




## 📚 Documentación

Guías detalladas:

### 📘 Manuales de usuario
- **Español**: [Manual de usuario](docs/manual_de_usuario.md)
- **English**: [User manual](docs/user_manual.md)

### ❓ Preguntas frecuentes
- **Español**: [Preguntas frecuentes (FAQ)](docs/preguntas_frecuentes.md)
- **English**: [Frequently Asked Questions](docs/faq.md)

### 📖 Glosario técnico
- **Español**: [Glosario](docs/glosario.md)
- **English**: [Glossary](docs/glossary.md)

### 📐 Arquitectura y diseño
- [Documentación de arquitectura](docs/architecture/forestguard_architecture.md)
- [Casos de Uso Detallados](docs/architecture/forestguard_use_cases.md)
- [Plan del Proyecto](docs/architecture/project_plan.md)
- [Manual de Marca (Branding)](docs/architecture/wildfire_branding.md)

---

## 🧩 Casos de uso (13 implementados)

### Lista completa de funcionalidades

| UC | Categoría | Nombre | Descripción | Estado |
|---|---|---|---|---|
| **UC-01** | Fiscalización | Auditoría Anti-Loteo | Verificar restricciones legales por incendios | ✅ DONE |
| **UC-02** | Fiscalización | Peritaje Judicial | Generar evidencia forense para causas judiciales | 🔜 PENDING |
| **UC-03** | Análisis | Recurrencia de Incendios | Detectar zonas con patrones repetitivos sospechosos | 🔜 PENDING |
| **UC-04** | Alertas | Capacidad de Carga | Alertas preventivas en parques por afluencia | 🔜 PENDING |
| **UC-05** | Análisis | Tendencias Históricas | Proyecciones de largo plazo y migración de riesgos | 🔜 PENDING |
| **UC-06** | Análisis | Reforestación | Monitoreo NDVI de recuperación vegetal (36 meses) | ⏳ IN PROGRESS |
| **UC-07** | Fiscalización | Certificación Legal | Emitir certificados digitales verificables | ✅ DONE |
| **UC-08** | Fiscalización | Cambio de Uso | Detectar construcción/agricultura ilegal post-fuego | 🔜 PENDING |
| **UC-09** | Participación | Denuncias Ciudadanas | Reportes públicos con evidencia satelital | 🔜 PENDING |
| **UC-10** | Análisis | Calidad del Dato | Métricas de confiabilidad para peritajes | 🔜 PENDING |
| **UC-11** | Análisis | Reportes Históricos | PDFs de incendios en áreas protegidas | 🔜 PENDING |
| **UC-12** | Operacional | Registro de Visitantes | Registro digital offline-first para refugios | 🔜 PENDING |
| **UC-13** | Análisis | Grilla de Incendios | Visualización y filtrado de eventos con índices optimizados | ✅ DONE |

---

## 🏗️ Arquitectura unificada

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

### 🆕 Módulos compartidos (unified architecture)

#### Vegetation analysis engine (VAE)
Módulo centralizado para análisis de vegetación usando NDVI:
- **UC-06**: Monitoreo de recuperación (reforestación)
- **UC-08**: Detección de cambios ilegales de uso

**Ventajas**: Evita duplicación de procesamiento GEE, mantiene consistencia metodológica.

#### Evidence reporting service (ERS)
Motor unificado para generación de reportes verificables:
- **UC-09**: Paquetes de evidencia para denuncias
- **UC-11**: Reportes históricos en áreas protegidas
- **UC-02**: Peritajes judiciales

**Ventajas**: PDFs homogéneos, verificación criptográfica centralizada, auditoría consistente.

---

## 🛠️ Stack tecnológico

### Backend
| Componente | Tecnología | Versión |
|------------|------------|---------|
| API Framework | FastAPI + Uvicorn | 0.104+ |
| ORM | SQLAlchemy + GeoAlchemy2 | 2.0+ |
| Async Tasks | Celery + Redis | 5.3+ |
| PDF Generation | WeasyPrint | - |

### Database & storage
| Componente | Tecnología | Límites |
|------------|------------|---------|
| Database | PostgreSQL 14 + PostGIS 3.0 | 500 MB (Supabase free) |
| Object storage | Cloudflare R2 | 10 GB free |
| Cache/queue | Redis | - |

### Data sources
| Source | Purpose | Frequency |
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

## 🚀 Quick start

### Requisitos

- Python 3.11+
- PostgreSQL 14+ con PostGIS
- Redis (para Celery)
- Cuenta en [Supabase](https://supabase.com) (base de datos)
- Cuenta Google Cloud con Earth Engine API habilitada

### Instalación local

```bash
# 1. Clonar repositorio
git clone https://github.com/nicolasgabrielh91/wildfire-recovery-argentina.git
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

## 📚 API endpoints

### Core endpoints

#### Legal audit (UC-01) ✅
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

#### Health check ✅
```bash
GET https://forestguard.freedynamicdns.org/health
```

Verifica estado de todos los componentes:
- Database (Supabase)
- Redis
- Google Earth Engine
- Cloudflare R2

---

## 📁 Estructura del proyecto

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
├── docs/                         # 📖 Documentación
│   ├── architecture/             # 🏗️ Arquitectura
│   │   ├── forestguard_use_cases.md # ✅ 11 casos de uso
│   │   ├── forestguard_architecture.md # ✅ Arquitectura técnica
│   │   └── project_plan.md       # ✅ Roadmap (70% complete)
│   ├── manual_de_usuario.md
│   └── ...
└── docker/                       # Docker configs
```

---

## 🔧 Configuración

### Variables de entorno requeridas

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

### Obtener credenciales

#### NASA FIRMS API key
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

**Deployment stack**:
- VM Shape: Ampere A1 (ARM) / 1 OCPU, 6GB RAM
- OS: Ubuntu 22.04 LTS
- Reverse proxy: Nginx
- Process manager: systemd / PM2
- Database: Supabase (PostgreSQL + PostGIS)
- Storage: Cloudflare R2

### Docker (desarrollo local)

```bash
# Desarrollo
docker-compose up -d

# Producción local
docker-compose -f docker-compose.prod.yml up -d
```

### Deploy manual (Oracle Cloud)

```bash
# 1. Conectar a VM
ssh ubuntu@<instance-ip>

# 2. Clonar repo
git clone https://github.com/nicolasgabrielh91/wildfire-recovery-argentina.git
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

## 📊 Scripts de mantenimiento

### Carga incremental de datos

```bash
# Descargar últimos 2 días de FIRMS
python scripts/load_firms_incremental.py

# Clustering de nuevas detecciones
python workers/tasks/clustering.py --mode incremental

# Enriquecer con datos climáticos
python workers/tasks/climate.py --days 7
```

---

## 📜 Marco legal

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

## 📈 Roadmap & estado

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

### ⏳ En desarrollo (20%)

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

### Mejores prácticas implementadas

- ✅ **RLS policies**: Row Level Security en Supabase
- ✅ **Rate limiting**: 
  - **Global**: 100 req/min por IP (Cloudflare/Nginx)
  - **App-level**: Bloqueo automático de IP tras 10 intentos fallidos/día + Alerta por Email opcional
- ✅ **Authentication**: 
  - API Key requerida para endpoints críticos (`/audit`, `/certificates`)
  - Header: `X-API-Key: <tu-clave>`
- ✅ **GEE credentials**: Never committed, env variables only
- ✅ **API versioning**: `/api/v1/` con deprecation policy
- ✅ **Health checks**: Componente-level monitoring
- ✅ **Error handling**: Mensajes sanitizados en producción (sin stack traces)
- ✅ **Audit Logging**: Trazabilidad completa de acciones críticas (`audit_events`)
- ✅ **SLOs Enforced**: Monitoreo de latencia (<400ms) vía Middleware

### Rate limits externos

| Service | Free tier limit |
|---------|------------------|
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

📧 Email: nicolasgabrielh91@gmail.com  
🔗 GitHub: [@Nicolasgh91](https://github.com/Nicolasgh91)  
💼 LinkedIn: [Nicolas Hruszczak](https://www.linkedin.com/in/nicolas-hruszczak/)

---

## 🙏 Agradecimientos

- **NASA FIRMS** - Datos abiertos de detección de incendios
- **Google Earth Engine** - Procesamiento satelital server-side, gratuito mediante cuenta educativa
- **Supabase** - Base de datos PostgreSQL + PostGIS - Free tier
- **FastAPI** - Framework web moderno con documentación auto-generada
- **Cloudflare** - CDN y object storage (R2)
---

## 🌍 Por qué ForestGuard importa

Los incendios forestales ya no son eventos aislados: son **riesgo sistémico**. La transparencia ambiental es clave para políticas públicas efectivas. Los datos abiertos solo generan impacto cuando se transforman en **evidencia accionable**. Su propósito es intentar prevenir y proporcionar información sobre los incendios forestales en Argentina.

**ForestGuard convierte datos en decisiones, y decisiones en responsabilidad.**

---

**Última actualización:** Enero 2026  
**Versión:** 2.0.0  
**Progreso:** 70% completado

[![Star on GitHub](https://img.shields.io/github/stars/nicolasgabrielh91/wildfire-recovery-argentina?style=social)](https://github.com/nicolasgabrielh91/wildfire-recovery-argentina)

---

# 🌲 ForestGuard API (English version)

**Geospatial intelligence platform for legal enforcement of wildfire recovery in Argentina**

> 🌍 **Read in spanish**: [Go to the spanish version](#-forestguard-api)

## ✨ Mission

**ForestGuard** is an environmental intelligence platform designed to **detect, analyze, audit, and document wildfires in Argentina**, turning raw satellite data into **actionable, traceable, and legally verifiable information**.

The project was born to solve a concrete problem: **fire data exists, but it is fragmented, difficult to interpret, and almost never becomes useful evidence for decision-making, accountability, or legal processes.**

ForestGuard transforms satellite data into **legal evidence** to enforce Article 22 bis of Law 26.815, which prohibits land use changes in fire-affected areas for 30-60 years.

## 🎯 Problem solved

Today, in Argentina:
* Wildfires are detected late or analyzed reactively.
* Satellite information (NASA FIRMS, VIIRS, MODIS) is scattered and technical.
* There is no unified system that:
  * Consolidates detections into **real events**.
  * Allows **auditing specific zones**.
  * Generates **verifiable evidence** for agencies, NGOs, or citizens.

**ForestGuard bridges the gap between open data and real decisions.**

ForestGuard converts millions of satellite detections into:
* 🔥 **Fire Events** (not just isolated dots)
* 🧭 **Geospatial Audits** by radius, plot, or location
* 📜 **Hashed Digital Certificates (PDF)**, publicly verifiable
* 📊 **National Historical Archive (2015–present)**
* 🌱 **Vegetation Recovery Monitoring** post-fire
* 🚧 **Illegal Land Use Change Detection**

## 📚 Documentation

We have prepared detailed guides for all user profiles:

### 📘 User manuals
- **English**: [User manual](docs/user_manual.md)
- **Spanish**: [Manual de usuario](docs/manual_de_usuario.md)

### ❓ FAQ
- **English**: [Frequently Asked Questions](docs/faq.md)
- **Spanish**: [Preguntas frecuentes](docs/preguntas_frecuentes.md)

### 📖 Glossary
- **English**: [Glossary](docs/glossary.md)
- **Spanish**: [Glosario](docs/glosario.md)

### 📐 Architecture & design
- [Architecture Documentation](docs/architecture/forestguard_architecture.md)
- [Detailed Use Cases](docs/architecture/forestguard_use_cases.md)
- [Project Plan](docs/architecture/project_plan.md)
- [Branding Guidelines](docs/architecture/wildfire_branding.md)

## 🧩 Use cases (13 implemented)

### Full feature list

| UC | Category | Name | Description | Status |
|---|---|---|---|---|
| **UC-01** | Enforcement | Land Use Audit | Verify legal restrictions due to fires | ✅ DONE |
| **UC-02** | Enforcement | Judicial Forensics | Generate forensic evidence for court cases | 🔜 PENDING |
| **UC-03** | Analysis | Fire Recurrence | Detect zones with suspicious repetitive patterns | 🔜 PENDING |
| **UC-04** | Alerts | Carrying Capacity | Preventive park alerts based on visitors | 🔜 PENDING |
| **UC-05** | Analysis | Historical Trends | Long-term projections and risk migration | 🔜 PENDING |
| **UC-06** | Analysis | Reforestation | NDVI monitoring of vegetation recovery (36 mos) | ⏳ IN PROGRESS |
| **UC-07** | Enforcement | Legal Certification | Issue verifiable digital certificates | ✅ DONE |
| **UC-08** | Enforcement | Land Use Change | Detect illegal construction/farming post-fire | 🔜 PENDING |
| **UC-09** | Participation | Citizen Reporting | Public reports with satellite evidence | 🔜 PENDING |
| **UC-10** | Analysis | Data Quality | Reliability metrics for forensics | 🔜 PENDING |
| **UC-11** | Analysis | Historical Reports | PDFs of fires in protected areas | 🔜 PENDING |
| **UC-12** | Operational | Visitor Registration | Offline-first digital registration for shelters | 🔜 PENDING |
| **UC-13** | Analysis | Fire Grid View | Fire events visualization and filtering (Optimized) | ✅ DONE |

## 🏗️ Unified architecture

ForestGuard uses a **hybrid API + Workers architecture** with shared modules to eliminate redundancy.

*(See Spanish section for detailed diagrams)*

### 🆕 Shared modules
*   **Vegetation analysis engine (VAE)**: Centralized vegetation analysis using NDVI.
*   **Evidence reporting service (ERS)**: Unified engine for verifiable report generation.

## 🚀 Quick start

### Requirements
*   Python 3.11+
*   PostgreSQL 14+ with PostGIS
*   Redis (for Celery)
*   Supabase Account (Database)
*   Google Cloud Account with Earth Engine API enabled

### Local installation

```bash
# 1. Clone repository
git clone https://github.com/nicolasgabrielh91/wildfire-recovery-argentina.git
cd wildfire-recovery-argentina

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
# Edit .env with your credentials

# 5. Load schema to Supabase
# Run database/schema_v0.1.sql in Supabase SQL Editor

# 6. Start services (Docker)
docker-compose up -d

# 7. Start API
uvicorn app.main:app --reload --port 8000
```

## 🚢 Deployment

### 🌐 Production (Oracle Cloud Free Tier) ✅

**Status**: LIVE
**URL**: https://forestguard.freedynamicdns.org
**API Docs**: https://forestguard.freedynamicdns.org/docs
**Infrastructure**: Oracle Cloud VM (Always Free)

## 🔒 Security

### Implemented controls
- **Authentication**: `X-API-Key` header required for `/audit` and `/certificates`.
- **Rate limiting**: IPs blocked after 10 requests/day. Optional alerts via email.
- **Error handling**: Production-safe error messages (no stack traces).
- **SSL/TLS**: Mandatory HTTPS via Let's Encrypt.
- **Audit Logging**: Centralized tracking of critical actions.
- **SLOs**: Enforced latency budgets (e.g., <400ms).

## 📄 License

MIT License - See [LICENSE](LICENSE) for details.

