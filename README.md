# ForestGuard

**Plataforma full-stack de inteligencia geoespacial que centraliza y expone de forma transparente datos satelitales públicos dispersos sobre incendios forestales en Argentina.**

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18+-61DAFB.svg)](https://reactjs.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14+-336791.svg)](https://postgresql.org)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

<p align="center">
  <img src="docs/assets/forestguard-banner.png" alt="ForestGuard Banner" width="800"/>
</p>

---

## Tabla de contenidos

- [Sobre este proyecto](#sobre-este-proyecto)
- [Qué demuestra este proyecto](#qué-demuestra-este-proyecto)
- [Qué hace ForestGuard](#qué-hace-forestguard)
- [Características](#características)
- [Arquitectura](#arquitectura)
- [Stack tecnológico](#stack-tecnológico)
- [Requisitos previos](#requisitos-previos)
- [Instalación](#instalación)
- [Configuración](#configuración)
- [Uso](#uso)
- [API Reference](#api-reference)
- [Casos de uso](#casos-de-uso)
- [Roadmap](#roadmap)
- [Qué aprendí construyendo esto](#qué-aprendí-construyendo-esto)
- [Contribución](#contribución)
- [Licencia](#licencia)

---

## Sobre este proyecto

ForestGuard es mi primera aplicación full-stack completa y mi primera API diseñada y construida integralmente. Es un proyecto de aprendizaje aplicado que está desplegado y corriendo en producción sobre infraestructura de costo cero.

La plataforma nació de una pregunta concreta: los datos satelitales sobre incendios forestales en Argentina existen y son públicos, pero están dispersos en múltiples APIs, formatos y servicios que requieren conocimiento técnico para acceder. No existía una herramienta unificada que permitiera a un ciudadano común explorar esa información de forma accesible.

ForestGuard resuelve eso: ingiere datos de NASA FIRMS, procesa imágenes de Sentinel-2 vía Google Earth Engine, integra datos climáticos de Open-Meteo, y presenta todo a través de una interfaz que permite investigar sin conocimientos técnicos previos.

---

## Qué demuestra este proyecto

- **Autonomía técnica**: Desarrollado íntegramente por una sola persona — todas las decisiones de arquitectura, infraestructura, modelado de datos y despliegue fueron tomadas y ejecutadas de forma independiente.
- **Capacidad arquitectónica**: Backend API (FastAPI) + workers asíncronos (Celery) + base de datos geoespacial (PostGIS + H3 indexing) + circuit breakers para servicios externos + storage distribuido.
- **Pensamiento sistémico**: El flujo completo va desde la ingesta automática de datos satelitales (NASA FIRMS cada 12h) hasta la generación de PDFs con cadena de custodia digital y hash SHA-256, pasando por clustering espacio-temporal, procesamiento de imágenes y análisis de vegetación.
- **Decisiones de costo cero**: Toda la infraestructura opera sobre free tiers — Oracle Cloud Free Tier (VM ARM64), Supabase Free Tier (PostgreSQL + Auth), Google Earth Engine Free Tier (procesamiento satelital), sin comprometer funcionalidad ni disponibilidad.

---

## Qué hace ForestGuard

ForestGuard centraliza datos satelitales públicos de múltiples fuentes (NASA FIRMS, Sentinel-2/Google Earth Engine, Open-Meteo) y los transforma en información estructurada, verificable y accesible para cualquier persona.

### El problema que resuelve

- +35,000 incendios registrados en Argentina entre 2015-2026
- Datos satelitales públicos dispersos en múltiples APIs y formatos incompatibles
- Sin herramienta unificada que permita a ciudadanos, ONGs o investigadores explorar esta información
- La Ley 26.815 establece restricciones de uso del suelo en zonas afectadas, pero no existía una forma accesible de consultar si un terreno está alcanzado

---

## Características

### Monitoreo en tiempo real
- Integración con NASA FIRMS (VIIRS/MODIS) cada 12 horas
- Visualización de incendios activos en mapa interactivo
- Clustering espacial inteligente con índices H3
- Alertas por proximidad a áreas protegidas

### Verificación de terreno
- Verificación de uso del suelo con consulta de restricciones (Ley 26.815)
- Certificados verificables con hash SHA-256 y QR
- Reportes técnicos con cadena de custodia digital
- Trazabilidad completa de evidencia

### Análisis y reportes
- Dashboard histórico con filtros avanzados y exportación CSV/GeoJSON
- Análisis de recurrencia y tendencias con forecasting
- Monitoreo de recuperación de vegetación (NDVI/NBR)
- Estadísticas públicas agregadas

### Evidencia satelital
- Imágenes Sentinel-2 con múltiples bandas (RGB, SWIR, NBR)
- Carrusel de imágenes pre/post incendio
- Thumbnails optimizados + HD on-demand
- Metadata reproducible para verificación independiente

---

## Arquitectura

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            FORESTGUARD ARCHITECTURE                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐                │
│  │   Frontend   │     │   Edge Fn    │     │   API        │                │
│  │   (React)    │────▶│  (Supabase)  │     │  (FastAPI)   │                │
│  │              │     │              │     │              │                │
│  └──────────────┘     └──────┬───────┘     └───────┬──────┘                │
│         │                    │                     │                        │
│         │                    ▼                     ▼                        │
│         │            ┌──────────────────────────────────┐                  │
│         │            │         Supabase                  │                  │
│         └───────────▶│  ┌─────────────┐  ┌────────────┐ │                  │
│                      │  │ PostgreSQL  │  │   Auth     │ │                  │
│                      │  │  + PostGIS  │  │            │ │                  │
│                      │  └─────────────┘  └────────────┘ │                  │
│                      └──────────────────────────────────┘                  │
│                                    │                                        │
│         ┌──────────────────────────┼──────────────────────────┐            │
│         ▼                          ▼                          ▼            │
│  ┌─────────────┐           ┌─────────────┐           ┌─────────────┐      │
│  │   Celery    │           │    Redis    │           │     GCS     │      │
│  │   Workers   │◀─────────▶│   Broker    │           │   Storage   │      │
│  └─────────────┘           └─────────────┘           └─────────────┘      │
│         │                                                                   │
│         │  ┌─────────────────────────────────────────────────────────┐    │
│         │  │                    External Services                     │    │
│         └─▶│  NASA FIRMS  │  Google Earth Engine  │  Open-Meteo      │    │
│            └─────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Componentes principales

| Componente | Tecnología | Propósito |
|------------|------------|-----------|
| **Frontend** | React + Vite + TailwindCSS | UI responsive con mapas interactivos |
| **API** | FastAPI + Uvicorn | Endpoints REST con auth y rate limiting |
| **Workers** | Celery + Redis | Procesamiento asíncrono (ingesta FIRMS, clustering, imágenes GEE, PDFs) |
| **Database** | PostgreSQL + PostGIS | Almacenamiento geoespacial con H3 indexing |
| **Auth** | Supabase Auth | Autenticación JWT y Row Level Security |
| **Storage** | Google Cloud Storage | Imágenes satelitales y reportes PDF |
| **Edge** | Supabase Edge Functions | Estadísticas públicas |

### Workers especializados

| Queue | Worker | Función |
|-------|--------|---------|
| `ingestion` | worker-ingestion | Descarga diaria NASA FIRMS (VIIRS/MODIS) |
| `clustering` | worker-clustering | ST-DBSCAN espacio-temporal sobre detecciones |
| `analysis` | worker-analysis | Imágenes GEE, análisis NDVI/NBR, reportes PDF, carrusel |

---

## Stack tecnológico

### Backend
- **Python 3.11+** — Lenguaje principal
- **FastAPI** — Framework web async
- **Celery** — Task queue distribuida
- **Redis** — Message broker y cache
- **SQLAlchemy + GeoAlchemy2** — ORM con soporte geoespacial
- **Alembic** — Migraciones de base de datos

### Frontend
- **React 19** — UI library
- **Vite** — Build tool
- **TypeScript** — Type safety
- **TailwindCSS** — Estilos utility-first
- **Shadcn/UI + Radix UI** — Componentes accesibles
- **Leaflet** — Mapas interactivos
- **TanStack React Query** — Server state management
- **i18next** — Internacionalización (ES/EN)

### Base de datos
- **PostgreSQL 14+** — Base de datos relacional
- **PostGIS** — Extensión geoespacial (Geography columns, ST_Distance, ST_Intersects)
- **H3** — Indexación espacial hexagonal (resolución 7-9)
- **Supabase** — Backend as a Service (Auth + RLS + Edge Functions)

### Servicios externos
- **NASA FIRMS** — Detección de focos de calor (VIIRS/MODIS)
- **Google Earth Engine** — Procesamiento de imágenes Sentinel-2 (NDVI, NBR, SWIR)
- **Open-Meteo** — Datos climáticos históricos (ERA5-Land)
- **MercadoPago** — Procesamiento de pagos (post-MVP)

### Infraestructura
- **Docker + Docker Compose** — Containerización (API + 3 workers + Redis + Celery Beat + Flower)
- **Nginx** — Reverse proxy con SSL
- **Oracle Cloud** — Hosting (VM Ampere ARM64, Free Tier)
- **Let's Encrypt** — Certificados SSL

---

## Requisitos previos

- **Python** >= 3.11
- **Node.js** >= 18
- **Docker** y **Docker Compose**
- **PostgreSQL** >= 14 con PostGIS
- Cuenta de **Supabase** (free tier)
- Cuenta de **Google Earth Engine** (free tier)
- Cuenta de **Google Cloud** para GCS (free tier)

---

## Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/your-org/wildfire-recovery-argentina.git
cd wildfire-recovery-argentina
```

### 2. Configurar variables de entorno

```bash
cp .env.template .env
# Editar .env con tus credenciales
```

### 3. Opción A: Instalación con Docker (recomendado)

```bash
# Construir y levantar todos los servicios
docker-compose up -d

# Verificar que los servicios estén corriendo
docker-compose ps
```

### 3. Opción B: Instalación manual

```bash
# Backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Frontend
cd frontend
npm install
```

### 4. Ejecutar migraciones

```bash
# Aplicar schema a Supabase
python run_migration.py

# O usar Alembic
alembic upgrade head
```

### 5. Iniciar servicios

```bash
# Backend (desarrollo)
uvicorn app.main:app --reload --port 8000

# Workers
celery -A workers.celery_app worker --queues=ingestion,reports --loglevel=info

# Frontend
npm run dev
```

---

## Configuración

### Variables de entorno requeridas

```env
# === Database ===
DATABASE_URL=postgresql://user:pass@host:port/db
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# === Redis ===
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1

# === Google Earth Engine ===
GEE_SERVICE_ACCOUNT=your-sa@project.iam.gserviceaccount.com
GEE_PRIVATE_KEY_BASE64=base64-encoded-key

# === Google Cloud Storage ===
GCS_BUCKET_IMAGES=forestguard-images
GCS_BUCKET_REPORTS=forestguard-reports

# === NASA FIRMS ===
FIRMS_MAP_KEY=your-firms-api-key

# === Security ===
API_KEY_SECRET=your-api-key-secret
HASH_SECRET=your-hash-secret-for-audits

# === SMTP (opcional) ===
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# === Environment ===
DEBUG=true
ENVIRONMENT=development
```

### Configuración de Google Earth Engine

1. Crear una cuenta de servicio en Google Cloud Console
2. Habilitar la API de Earth Engine
3. Descargar el JSON de credenciales
4. Codificar en base64 y configurar `GEE_PRIVATE_KEY_BASE64`

```bash
base64 -w 0 credentials.json > credentials_base64.txt
```

---

## Uso

### Acceder a la aplicación

- **Frontend**: http://localhost:5173
- **API Docs**: http://localhost:8000/docs
- **API ReDoc**: http://localhost:8000/redoc

### Comandos útiles

```bash
# Ejecutar tests
pytest

# Tests con cobertura
pytest --cov=app --cov-report=html

# Linting
flake8 app
black app

# Generar migración
alembic revision --autogenerate -m "descripción"

# Aplicar migraciones
alembic upgrade head
```

---

## API Reference

### Endpoints principales

| Método | Endpoint | Descripción | Auth |
|--------|----------|-------------|------|
| `GET` | `/api/v1/fires` | Listar incendios con filtros | Público |
| `GET` | `/api/v1/fires/{id}` | Detalle de incendio | Público |
| `GET` | `/api/v1/fires/stats` | KPIs del dashboard | API Key o JWT |
| `POST` | `/api/v1/audit/land-use` | Verificación de terreno | JWT |
| `GET` | `/api/v1/quality/fire-event/{id}` | Score de calidad | API Key |
| `GET` | `/api/v1/analysis/recurrence` | Análisis de recurrencia H3 | API Key |
| `POST` | `/api/v1/reports/judicial` | Generar reporte técnico | Público (MVP actual) |
| `POST` | `/api/v1/contact` | Formulario de contacto | Público |
| `GET` | `/functions/v1/public-stats` | Estadísticas públicas | Público |

### Autenticación

```bash
# Usando API Key
curl -H "X-API-Key: your-api-key" \
     https://api.forestguard.com.ar/api/v1/fires
```

```bash
# Usando JWT (ejemplo para /audit/land-use)
curl -X POST \
     -H "Authorization: Bearer <jwt>" \
     -H "Content-Type: application/json" \
     -d '{"lat": -34.6037, "lon": -58.3816, "radius_meters": 1000}' \
     https://api.forestguard.com.ar/api/v1/audit/land-use
```

### Ejemplo: Verificación de terreno

```bash
curl -X POST \
     -H "Authorization: Bearer <jwt>" \
     -H "Content-Type: application/json" \
     -d '{"lat": -34.6037, "lon": -58.3816, "radius_meters": 1000}' \
     https://api.forestguard.com.ar/api/v1/audit/land-use
```

**Respuesta:**
```json
{
  "is_prohibited": true,
  "prohibition_until": "2085-03-15",
  "fires_found": 2,
  "fires": [
    {
      "id": "uuid",
      "start_date": "2025-03-15",
      "estimated_area_hectares": 150.5,
      "protected_area": "Reserva Natural XYZ"
    }
  ],
  "audit_hash": "sha256:abc123...",
  "audit_id": "uuid"
}
```

---

## Casos de uso

Para documentación detallada de cada caso de uso, ver [docs/use_cases.md](docs/use_cases.md).

| UC | Nombre | Estado | Descripción |
|----|--------|--------|-------------|
| UC-F01 | Contacto y soporte | Implementado | Formulario con adjuntos, rate limiting y fallback SMTP sincrónico |
| UC-F02 | Estadísticas públicas | Implementado | Datos agregados anónimos vía Edge Function con cache HTTP |
| UC-F03 | Histórico y dashboard | Implementado | Dashboard interactivo con filtros, KPIs y exportación CSV/GeoJSON |
| UC-F04 | Calidad del dato | Implementado | Score de confiabilidad ponderado (detecciones, imágenes, clima, independientes) |
| UC-F05 | Recurrencia y tendencias | Implementado | Análisis espacial con índices H3 y forecasting de tendencias |
| UC-F06 | Verificación de terreno | Implementado | Consulta de restricciones Ley 26.815 con evidencia satelital verificable |
| UC-F08 | Carrusel satelital | Implementado | Thumbnails diarios de incendios activos con priorización inteligente |
| UC-F09 | Reportes de cierre | Implementado | Comparativas pre/post incendio con cálculo de severidad (dNBR) |
| UC-F11 | Reportes técnicos verificables | Implementado | PDFs con cadena de custodia, hash SHA-256 y QR de verificación |
| UC-F13 | Episodios macro | Implementado | Clustering de eventos con versionado de parámetros y metadata reproducible |

---

## Roadmap

### Completado
- [x] Fase 0: Tablas base (clima, metadata)
- [x] Fase 1: Modelo de datos (H3, episodios, parámetros)
- [x] T2.1-T2.5: API endpoints principales
- [x] T2.6: Verificación de terreno
- [x] Fase 3: Workers de imágenes (carrusel, thumbnails)
- [x] Frontend: UI completa con i18n (ES/EN)

### En progreso
- [ ] Fase 4: Reportes PDF (cierre, técnicos)
- [ ] Fase 5: Testing y observabilidad

### Próximamente
- [ ] UC-F07: Registro de visitantes offline
- [ ] UC-F10: Certificación monetizada
- [ ] UC-F12: VAE (detección de cambio de uso del suelo por ML)
- [ ] Integración MercadoPago completa
- [ ] App móvil PWA

---

## Qué aprendí construyendo esto

- **Async-first architecture**: Diseñar con task queues (Celery) desde el inicio simplifica el manejo de operaciones lentas (GEE tarda 30s-5min por imagen), pero introduce complejidad en monitoreo, retries y dead letter queues. La separación en queues especializadas (ingestion, clustering, analysis) fue una decisión determinante para poder escalar workers de forma independiente.

- **Reproducibilidad satelital**: Las imágenes de Sentinel-2 son ópticas y dependen de las condiciones atmosféricas. Un sistema que depende de ellas necesita manejar progresión de umbrales de nubosidad (10% → 20% → 30% → 50%), fallbacks a fechas alternativas, y comunicar claramente al usuario por qué una imagen puede no estar disponible.

- **Seguridad por defecto con Supabase**: Implementar Row Level Security desde el inicio es una decisión arquitectónica, no una feature. Combinado con validación JWT vía JWKS y separación de service key vs anon key, permite que la base de datos sea el enforcement point de autorización.

- **Optimización bajo restricciones de free tiers**: Oracle Cloud Free Tier (1GB RAM ARM64), Supabase Free (500MB DB), GEE Free (50k requests/day). Estas restricciones forzaron decisiones de diseño reales: connection pooling agresivo, pool_size=5 con max_overflow=10, reciclado de conexiones cada hora, thumbnails optimizados (768x576) en lugar de imágenes full-resolution.

- **H3 para consultas geoespaciales eficientes**: Convertir lat/lon a índices H3 (resolución 8) permite agregar datos espaciales sin joins geográficos costosos. Las materialized views sobre H3 cells hacen que los heatmaps de recurrencia sean consultas simples sobre índices en lugar de operaciones geométricas.

- **Circuit breakers para APIs externas**: Google Earth Engine tiene rate limits estrictos (1 req/s, 50k/día). Implementar circuit breaker con estados open/half-open/closed evita cascadas de failures y permite degradación controlada cuando GEE no responde.

- **Separación service layer / API / workers**: Mantener la lógica de negocio en servicios inyectables (no en routes ni en tasks) permite que el mismo servicio sea invocado desde un endpoint API o desde un worker Celery sin duplicación de código.

---

## Contribución

Las contribuciones son bienvenidas. Por favor lee nuestra [guía de contribución](CONTRIBUTING.md).

### Proceso

1. Fork del repositorio
2. Crear branch (`git checkout -b feature/nueva-funcionalidad`)
3. Commit de cambios (`git commit -m 'Agregar nueva funcionalidad'`)
4. Push al branch (`git push origin feature/nueva-funcionalidad`)
5. Abrir Pull Request

### Convenciones de código

- **Python**: PEP 8, Black formatter, type hints
- **JavaScript/React**: ESLint, Prettier
- **Commits**: Conventional Commits
- **Branches**: `feature/`, `fix/`, `docs/`

---

## Licencia

Este proyecto está bajo la licencia MIT. Ver [LICENSE](LICENSE) para más detalles.

---

## Fuentes de datos públicos integrados

- **NASA FIRMS** — Detección de focos de calor (VIIRS/MODIS)
- **ESA/Copernicus** — Imágenes Sentinel-2 (10m resolución, multibanda)
- **Google Earth Engine** — Procesamiento y análisis de imágenes satelitales
- **Open-Meteo** — Datos climáticos históricos (ERA5-Land)
- **IGN / APN** — Geometrías de áreas protegidas y regiones políticas

---

## Contacto

- **Website**: [forestguard.freedynamicdns.org](https://forestguard.freedynamicdns.org)
- **Email**: nicolasgabrielh91@gmail.com — Analista Técnico Funcional

---

<p align="center">
  <img src="docs/assets/footer-trees.png" alt="Trees" width="600"/>
</p>
