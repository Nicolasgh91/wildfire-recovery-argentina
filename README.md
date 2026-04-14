# 🔥 Huella del Fuego

**Plataforma de inteligencia geoespacial para monitoreo de incendios forestales históricos y análisis de recuperación vegetal en Argentina.**

> Transforma datos satelitales de NASA FIRMS y Sentinel-2 en evidencia verificable para entender que sucedió en los terrenos afectados durante los años posteriores al incendio.

🌐 [huelladelfuego.com.ar](https://huelladelfuego.com.ar)

---

## El problema

Argentina pierde miles de hectáreas cada año por incendios forestales. La Ley 26.815 prohíbe el cambio de uso del suelo en zonas quemadas por 30 a 60 años, pero la fiscalización es manual, lenta y carece de evidencia técnica reproducible. Escribanías, fiscalías y ONGs no cuentan con herramientas accesibles para verificar si un terreno fue afectado por fuego ni para monitorear su recuperación vegetal.

## La solución

Huella del fuego automatiza la detección, agrupación y seguimiento de incendios forestales (API desarrollada integramente por https://www.escalatunegocioconia.com/) integrando múltiples fuentes satelitales. Genera evidencia y brinda la posibilidad de analizar la recuperación de la vegetación mes a mes (o rango de fecha particular) mediante análisis NDVI sobre imágenes Sentinel-2.

---

## Características principales

- **Detección automática de incendios** — Ingesta diaria de datos NASA FIRMS (VIIRS/MODIS) con clustering espacial DBSCAN e indexación hexagonal H3.
- **Monitoreo de recuperación vegetal (VAE)** — Análisis NDVI mensual vía Google Earth Engine con clasificación automática: recuperación temprana, moderada, avanzada, completa, estancada o anomalía.
- **Verificación del suelo** — Búsqueda por coordenadas con cruce contra áreas protegidas y generación de evidencia con disclaimers legales (Ley 26.815 / Ley 27.604).
- **Creación de reportes** — PDFs con hash verificable, cronología satelital y metadata.
- **Enriquecimiento geográfico** — Asignación automática de provincia y departamento a cada evento mediante PostGIS y datos del Georef argentino.
- **Dashboard y mapa interactivo** — Visualización de episodios activos, históricos y KPIs de recurrencia con heatmaps H3.
- **Thumbnails satelitales** — Renderizado server-side desde GEE con cobertura espacial evaluada y bbox calculado desde perímetros reales.

---

## Arquitectura

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENTE                                  │
│   React 19 + TypeScript + Vite 7 + Tailwind + Leaflet          │
│                  Cloudflare Pages (CDN)                         │
└──────────────────────┬──────────────────────────────────────────┘
                       │ HTTPS
┌──────────────────────▼──────────────────────────────────────────┐
│                      NGINX (reverse proxy)                      │
└──────────┬─────────────────────────────┬────────────────────────┘
           │                             │
┌──────────▼──────────┐    ┌─────────────▼────────────────────────┐
│    FastAPI (API)     │    │         Celery workers               │
│  Endpoints REST     │    │  ┌────────────┐  ┌────────────────┐  │
│  JWT + API keys     │    │  │ worker-fast │  │  worker-gee    │  │
│  Rate limiting      │    │  │ (ingesta,  │  │  (GEE/VAE,     │  │
│  Pydantic schemas   │    │  │  clustering)│  │   recovery,    │  │
│                     │    │  │            │  │   thumbnails)  │  │
└──────────┬──────────┘    │  └────────────┘  └────────────────┘  │
           │               │  ┌────────────┐                      │
           │               │  │ celery-beat│ (scheduler diario)   │
           │               │  └────────────┘                      │
           │               └──────────────┬───────────────────────┘
           │                              │
┌──────────▼──────────────────────────────▼───────────────────────┐
│              PostgreSQL + PostGIS (Supabase)                     │
│    RLS · Funciones PostGIS · Vistas materializadas              │
└─────────────────────────────────────────────────────────────────┘
           │                              │
┌──────────▼──────────┐    ┌──────────────▼───────────────────────┐
│   Redis (broker)    │    │       Servicios externos              │
│   Celery queues     │    │  NASA FIRMS · Google Earth Engine     │
│   Rate limit store  │    │  Georef AR · OCI Object Storage      │
└─────────────────────┘    └──────────────────────────────────────┘
```

El sistema sigue un principio **async-first**: toda operación pesada (imágenes satelitales, clustering, análisis NDVI, generación de PDFs) se delega a workers de Celery, y la API responde con `202 Accepted` de forma inmediata.

---

## Stack tecnológico

| Capa | Tecnologías |
|---|---|
| **Frontend** | React 19, TypeScript, Vite 7, Tailwind CSS, Leaflet, pnpm |
| **Backend** | Python, FastAPI, Celery, Redis, Pydantic |
| **Base de datos** | PostgreSQL + PostGIS (Supabase), H3 hexagonal indexing |
| **Satelital / geo** | Google Earth Engine (Sentinel-2 L2A), NASA FIRMS (VIIRS/MODIS) |
| **Infraestructura** | Docker Compose, Nginx, Oracle Cloud ARM64 VM |
| **CI/CD** | GitHub Actions (frontend), Cloudflare Pages |
| **Storage** | OCI Object Storage (thumbnails, reportes PDF) |
| **Autenticación** | Supabase Auth, Google OAuth, JWT |

---

## Decisiones técnicas destacadas

| Decisión | Elección | Justificación |
|---|---|---|
| Grilla espacial | H3 (BIGINT) | 10× menos almacenamiento, agregaciones rápidas para heatmaps |
| Procesamiento pesado | Celery async workers | Desacople total de la API, resiliencia ante fallos de GEE |
| Reportes | Hash SHA-256 + metadata reproducible | Consulta histórica descargable en PDF |
| Baseline NDVI | `qualityMosaic('NDVI')` 365 días pre-incendio | Captura el pico anual de vegetación, superior a ventanas cortas |
| Bbox de episodios | Calculado desde perímetros (`ST_XMin/YMin/XMax/YMax`) | Los centroides producen áreas microscópicas inutilizables |
| Trazabilidad del dato | Append-only inmutable | Los datos crudos son procesados y el historial de cambios realizados se persiste en la base de datos. Incluye versionado ante actuzalicaciones en el agrupamiento de los datos |
| Operación | Costo cero (free tiers) | Supabase 500 MB, GEE 50K req/día, OCI 1gb free tier |

---

## Módulos del sistema

### Pipeline de datos (automatizado)
```
NASA FIRMS → Ingesta diaria → DBSCAN clustering → Eventos → Episodios
                                    ↓
                        Enriquecimiento geográfico
                        (provincia + departamento)
```

### Análisis de recuperación vegetal (VAE)
```
Evento de incendio → Baseline NDVI (365d pre-fuego)
        ↓
Análisis mensual → NDVI actual vs baseline → Clasificación
        ↓
early_recovery | moderate | advanced | full | stalled | anomaly
        ↓
Detección de cambio de uso del suelo → Alertas (Ley 26.815)
```

### Reportes
```
Solicitud → Worker async → GEE imagery + clima + metadata
        ↓
    PDF con hash SHA-256 + QR de verificación
        ↓
    OCI Object Storage → URL de descarga
```

---

## Estado del proyecto

### Completado
- Ingesta automatizada NASA FIRMS con ingesta manual de CSV como fallback
- Clustering espacial DBSCAN con versionado y H3 indexing
- Pipeline VAE completo (14 fases, 58 tareas): análisis NDVI, clasificación, backfill histórico
- Enriquecimiento geográfico con ~530 departamentos argentinos
- Thumbnails satelitales con evaluación de cobertura espacial
- Reportes PDF con hash y cadena de custodia
- Suite de tests (unitarios, integración, E2E)
- Deploy en producción (Oracle Cloud ARM64 + Cloudflare Pages)

### En progreso
- Backfill VAE histórico 2016–2025
- Corrección de schedule de clustering diario (celery-beat)

### Planificado
- Aplicación móvil vía Capacitor / Google Play
- Migración de builds a GHCR
- KPIs de recurrencia con heatmaps H3 interactivos

---

## Ejecución local

```bash
# Clonar el repositorio
git clone https://github.com/<usuario>/forestguard.git
cd forestguard

# Configurar variables de entorno
cp .env.template .env
# Editar .env con credenciales de Supabase, GEE, Redis, etc.

# Levantar servicios
docker compose up -d

# Frontend (en otra terminal)
cd frontend
pnpm install
pnpm dev
```

**Requisitos:** Docker, Docker Compose, pnpm, cuenta de Google Earth Engine (free tier), proyecto en Supabase.

---

## Estructura del repositorio

```
forestguard/
├── app/
│   ├── api/routes/          # Endpoints REST (FastAPI)
│   ├── core/                # Config, auth, rate limiting, circuit breaker
│   ├── models/              # SQLAlchemy / Pydantic models
│   ├── services/            # Lógica de negocio (GEE, VAE, reportes)
│   └── workers/tasks/       # Tareas Celery (ingesta, clustering, recovery)
├── frontend/
│   ├── src/components/      # React components (mapa, dashboard, monitoring)
│   ├── src/pages/           # Rutas principales
│   └── src/services/        # API clients
├── database/
│   └── functions/           # Funciones PostGIS (assign_province_department)
├── docs/                    # ADRs, specs, runbooks
├── tests/                   # Unit, integration, E2E
├── docker-compose.yml
└── .github/workflows/       # CI/CD pipelines
```

---

## Contexto 

Este sistema opera bajo el marco regulatorio argentino:
- **Ley 26.815 / 27.604** — Manejo del fuego y prohibición de cambio de uso del suelo en zonas quemadas.
- **Ley 25.326** — Protección de datos personales.

Las clasificaciones de cambio de uso del suelo son generadas algorítmicamente sin validación de campo. Toda la información sobre violaciones potenciales incluye disclaimers legales obligatorios y se presenta con indicadores discretos (decisión D-03).

---

## Sobre el proyecto

Proyecto diseñado, arquitectado e implementado de forma independiente como primera aplicación full-stack, combinando análisis funcional, diseño de arquitectura y desarrollo end-to-end. Tiene un fin académico.

**Competencias demostradas:**
- Diseño de arquitectura distribuida (API + workers async + message broker)
- Integración de APIs satelitales (Google Earth Engine, NASA FIRMS)
- Modelado de datos geoespaciales (PostGIS, H3)
- Pipeline de datos con procesamiento asíncrono (Celery + Redis)
- Seguridad por capas (JWT, RLS, rate limiting, audit trail inmutable)
- Infraestructura cloud (Docker, Oracle Cloud ARM64, Cloudflare)
- CI/CD con GitHub Actions
- Dominio funcional: legislación ambiental argentina, remote sensing, NDVI

---

## Licencia

Este proyecto es software propietario. Todos los derechos reservados.

---

<p align="center">
  <i>Construido con datos abiertos de NASA y ESA para la protección de los bosques argentinos.</i>
</p>
