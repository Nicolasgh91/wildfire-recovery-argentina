# 🌲 ForestGuard

**Plataforma de inteligencia geoespacial para la fiscalización legal y monitoreo de recuperación de zonas afectadas por incendios forestales en Argentina.**

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18+-61DAFB.svg)](https://reactjs.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14+-336791.svg)](https://postgresql.org)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

<p align="center">
  <img src="docs/assets/forestguard-banner.png" alt="ForestGuard Banner" width="800"/>
</p>

---

## 📋 Tabla de contenidos

- [Descripción](#-descripción)
- [Características](#-características)
- [Arquitectura](#-arquitectura)
- [Stack tecnológico](#-stack-tecnológico)
- [Requisitos previos](#-requisitos-previos)
- [Instalación](#-instalación)
- [Configuración](#-configuración)
- [Uso](#-uso)
- [API Reference](#-api-reference)
- [Casos de uso](#-casos-de-uso)
- [Roadmap](#-roadmap)
- [Contribución](#-contribución)
- [Licencia](#-licencia)

---

## 🎯 Descripción

ForestGuard transforma datos satelitales (NASA FIRMS, Sentinel-2/Google Earth Engine) en **evidencia legal verificable** y reportes auditables para el cumplimiento de la **Ley 26.815** (Art. 22 bis) de Argentina, que establece prohibiciones de uso del suelo de 30 a 60 años en zonas afectadas por incendios forestales.

### ¿Por qué ForestGuard?

- 🔥 **+35,000 incendios** registrados en Argentina entre 2015-2026
- ⚖️ **Vacío de fiscalización** en la aplicación de la Ley 26.815
- 🛰️ **Datos satelitales infrautilizados** para evidencia legal
- 📊 **Falta de herramientas** accesibles para ONGs, fiscalías y ciudadanos

---

## ✨ Características

### Monitoreo en tiempo real
- 🛰️ Integración con NASA FIRMS (VIIRS/MODIS) cada 12 horas
- 🗺️ Visualización de incendios activos en mapa interactivo
- 📍 Clustering espacial inteligente con índices H3
- 🔔 Alertas por proximidad a áreas protegidas

### Fiscalización legal
- ⚖️ Auditoría de uso del suelo con cálculo automático de prohibiciones
- 📜 Certificados legales verificables con hash SHA-256 y QR
- 📋 Reportes judiciales con cadena de custodia digital
- 🔐 Trazabilidad completa de evidencia

### Análisis y reportes
- 📈 Dashboard histórico con filtros avanzados y exportación
- 🔄 Análisis de recurrencia y tendencias con forecasting
- 🌱 Monitoreo de recuperación de vegetación (NDVI/NBR)
- 📊 Estadísticas públicas agregadas

### Evidencia satelital
- 🖼️ Imágenes Sentinel-2 con múltiples bandas (RGB, SWIR, NBR)
- 📸 Carrusel de imágenes pre/post incendio
- 🔬 Thumbnails optimizados + HD on-demand
- 📍 Metadata reproducible para verificación independiente

---

## 🏗️ Arquitectura

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
| **Workers** | Celery + Redis | Procesamiento asíncrono (GEE, PDFs) |
| **Database** | PostgreSQL + PostGIS | Almacenamiento geoespacial |
| **Auth** | Supabase Auth | Autenticación y RLS |
| **Storage** | Google Cloud Storage | Imágenes y reportes |
| **Edge** | Supabase Edge Functions | Estadísticas públicas |

---

## 🛠️ Stack tecnológico

### Backend
- **Python 3.11+** - Lenguaje principal
- **FastAPI** - Framework web async
- **Celery** - Task queue distribuida
- **Redis** - Message broker y cache
- **SQLAlchemy + GeoAlchemy2** - ORM con soporte geoespacial
- **Alembic** - Migraciones de base de datos

### Frontend
- **React 18** - UI library
- **Vite** - Build tool
- **TypeScript** (opcional) - Type safety
- **TailwindCSS** - Estilos utility-first
- **Shadcn/UI** - Componentes accesibles
- **MapLibre GL** - Mapas vectoriales
- **deck.gl** - Visualización H3

### Base de datos
- **PostgreSQL 14+** - Base de datos relacional
- **PostGIS** - Extensión geoespacial
- **Supabase** - Backend as a Service

### Servicios externos
- **NASA FIRMS** - Detección de focos de calor
- **Google Earth Engine** - Procesamiento de imágenes satelitales
- **Open-Meteo** - Datos climáticos (ERA5-Land)
- **MercadoPago** - Procesamiento de pagos (post-MVP)

### Infraestructura
- **Docker + Docker Compose** - Containerización
- **Nginx** - Reverse proxy
- **Oracle Cloud** - Hosting (VM Ampere/ARM64)

---

## 📦 Requisitos previos

- **Python** >= 3.x
- **Node.js** >= 18
- **Docker** y **Docker Compose**
- **PostgreSQL** >= 14 con PostGIS
- Cuenta de **Supabase** (free tier)
- Cuenta de **Google Earth Engine** (free tier)
- Cuenta de **Google Cloud** para GCS (free tier)

---

## 🚀 Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/your-org/wildfire-recovery-argentina.git
cd wildfire-recovery-argentina
```

### 2. Configurar variables de entorno

```bash
cp .env.example .env
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
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Frontend
cd ../frontend
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

## ⚙️ Configuración

### Variables de entorno requeridas

```env
# === Database ===
DATABASE_URL=postgresql://user:pass@host:port/db
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# === Redis ===
REDIS_URL=redis://localhost:6379/0

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

## 📖 Uso

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

## 📚 API Reference

### Endpoints principales

| Método | Endpoint | Descripción | Auth |
|--------|----------|-------------|------|
| `GET` | `/api/v1/fires` | Listar incendios con filtros | API Key |
| `GET` | `/api/v1/fires/{id}` | Detalle de incendio | API Key |
| `GET` | `/api/v1/fires/stats` | KPIs del dashboard | API Key |
| `POST` | `/api/v1/audit/land-use` | Auditoría legal | API Key |
| `GET` | `/api/v1/quality/fire-event/{id}` | Score de calidad | API Key |
| `GET` | `/api/v1/analysis/recurrence` | Análisis de recurrencia H3 | API Key |
| `POST` | `/api/v1/reports/judicial` | Generar reporte judicial | API Key |
| `POST` | `/api/v1/contact` | Formulario de contacto | Público |
| `GET` | `/functions/v1/public-stats` | Estadísticas públicas | Público |

### Autenticación

```bash
# Usando API Key
curl -H "X-API-Key: your-api-key" \
     https://api.forestguard.com.ar/api/v1/fires
```

### Ejemplo: Auditoría legal

```bash
curl -X POST \
     -H "X-API-Key: your-api-key" \
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

## 🎯 Casos de uso

### UC-F01: Contacto y soporte
Formulario de contacto con adjuntos (máx 5MB) y rate limiting.

### UC-F02: Estadísticas públicas
Datos agregados anónimos vía Edge Function con cache HTTP.

### UC-F03: Histórico y dashboard
Dashboard interactivo con filtros, KPIs, y exportación CSV/GeoJSON.

### UC-F04: Calidad del dato
Score de confiabilidad ponderado (detecciones 40%, imágenes 20%, clima 20%, independientes 20%).

### UC-F05: Recurrencia y tendencias
Análisis espacial con índices H3 y forecasting de tendencias.

### UC-F06: Auditoría legal
Determinación de prohibiciones según Ley 26.815 con evidencia verificable.

### UC-F08: Carrusel satelital
Thumbnails diarios de incendios activos con priorización inteligente.

### UC-F09: Reportes de cierre
Comparativas pre/post incendio con cálculo de severidad (dNBR).

### UC-F11: Reportes judiciales
PDFs con cadena de custodia, hash SHA-256 y QR de verificación.

### UC-F13: Episodios macro
Clustering de eventos con versionado de parámetros y metadata reproducible.

---

## 🗺️ Roadmap

### ✅ Completado (56%)
- [x] Fase 0: Tablas base (clima, metadata)
- [x] Fase 1: Modelo de datos (H3, episodios, parámetros)
- [x] T2.1-T2.5: API endpoints principales

### ⏳ En progreso
- [ ] T2.6: Auditoría legal

### 📅 Próximamente
- [ ] Fase 3: Workers de imágenes
- [ ] Fase 4: Reportes PDF
- [ ] Fase 5: Testing y observabilidad

### 🔮 Post-MVP
- [ ] UC-F07: Registro de visitantes offline
- [ ] UC-F10: Certificación legal monetizada
- [ ] UC-F12: VAE (recuperación de vegetación)
- [ ] Integración MercadoPago
- [ ] App móvil PWA

---

## 🤝 Contribución

¡Las contribuciones son bienvenidas! Por favor lee nuestra [guía de contribución](CONTRIBUTING.md).

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

## 📄 Licencia

Este proyecto está bajo la licencia MIT. Ver [LICENSE](LICENSE) para más detalles.

---

## Información pública recolectada en esta API

- **NASA FIRMS** por los datos de detección de incendios
- **ESA/Copernicus** por las imágenes Sentinel-2
- **Google Earth Engine** por el procesamiento satelital
- **Open-Meteo** por los datos climáticos

---

## 📞 Contacto

- **Website**: [forestguard.com.ar](https://forestguard.freedynamicdns.org/docs) (API docs de momento. Web UI en proceso)
- **Email**: nicolasgabrielh91@gmail.com - Analista Técnico Funcional
- **Twitter**: [@ForestGuardAR](https://twitter.com/ForestGuardAR)

---

<p align="center">
  Hecho con ❤️ para proteger nuestros bosques
</p>

<p align="center">
  <img src="docs/assets/footer-trees.png" alt="Trees" width="600"/>
</p>