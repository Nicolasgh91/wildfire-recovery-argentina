# 🌲 ForestGuard API

**Plataforma de inteligencia geoespacial para fiscalización legal de incendios forestales en Argentina**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-009688.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14+-blue.svg)](https://www.postgresql.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

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

Todo con una arquitectura moderna, escalable y orientada a APIs.



## 🧩 Casos de uso principales

### 1️⃣ Detección y análisis histórico de incendios

* Consolidación de datos FIRMS (VIIRS / MODIS)
* Normalización de sensores y métricas térmicas
* Clustering espacio-temporal para identificar **incendios reales**

👉 Ideal para análisis ambiental, investigación y periodismo de datos.

---

### 2️⃣ Auditoría ambiental por ubicación

Dado un punto geográfico:

```json
{
  "lat": -27.4658,
  "lon": -58.8346,
  "radius_meters": 500,
  "cadastral_id": "..."
}
```

ForestGuard responde:

* incendios históricos cercanos
* recurrencia
* severidad
* contexto temporal

👉 Útil para municipios, desarrolladores inmobiliarios, ONGs y ciudadanos.

---

### 3️⃣ Certificados legales verificables

ForestGuard puede generar:

* 📄 **Certificados PDF** con branding
* 🔐 Hash SHA-256 del contenido
* 🔎 QR de verificación pública

Cada certificado puede descargarse vía API y verificarse externamente.

👉 Aplicable a:

* denuncias ambientales
* compliance
* procesos administrativos o legales


## 🏗️ Arquitectura (alto nivel)

```text
┌──────────────┐
│ NASA FIRMS   │
│ (VIIRS/MODIS│
└──────┬───────┘
       │ ETL
┌──────▼────────────┐
│ Ingesta & Normal. │
└──────┬────────────┘
       │
┌──────▼────────────┐
│ Base Geoespacial  │  PostgreSQL + PostGIS
└──────┬────────────┘
       │
┌──────▼────────────┐
│ Clustering        │  DBSCAN / heurísticas
└──────┬────────────┘
       │
┌──────▼────────────┐
│ API REST (FastAPI)│
└──────┬────────────┘
       │
┌──────▼────────────┐
│ Auditorías / PDFs │
└───────────────────┘
```

---

## 🗄️ Modelo de datos (resumen)

Entidades principales:

* **fire_detections**: detecciones satelitales normalizadas
* **fire_events**: incendios consolidados (cluster)
* **regions**: regiones / áreas geográficas
* **certificates**: certificados emitidos y verificables

Relación conceptual:

```text
fire_detections ──▶ fire_events
        │                 │
        ▼                 ▼
     regions         certificates
```

El diseño prioriza:

* trazabilidad
* reproducibilidad
* auditoría histórica

---

## 🛠️ Stack tecnológico

* **Backend**: Python, FastAPI
* **DB**: PostgreSQL + PostGIS (Supabase)
* **ETL**: Python, Pandas
* **Clustering**: scikit-learn (DBSCAN)
* **PDFs**: FPDF (branding + QR + hash)
* **Infra**: Docker-ready, cloud-agnostic

---

## 🌍 Por qué ForestGuard importa

* Los incendios forestales ya no son eventos aislados: son **riesgo sistémico**.
* La transparencia ambiental es clave para políticas públicas y privadas.
* Los datos abiertos solo generan impacto cuando se transforman en evidencia.

**ForestGuard convierte datos en decisiones, y decisiones en responsabilidad.**

---

## 💡 Estado del proyecto

* ✔️ Pipeline histórico completo (2015–presente)
* ✔️ Ingesta incremental diaria
* ✔️ Clustering de incendios
* ✔️ Auditoría geoespacial
* ✔️ Certificados PDF verificables
* 🔜 Dashboard público / API monetizable







## 🚀 Quick Start

### Requisitos

- Python 3.11+
- PostgreSQL 14+ con PostGIS
- Cuenta en [Supabase](https://supabase.com) (base de datos)

### Instalación Local

```bash
# 1. Clonar repositorio
git clone https://github.com/tu-usuario/forestguard-api.git
cd forestguard-api

# 2. Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales de Supabase

# 5. Iniciar servidor
uvicorn app.main:app --reload --port 8000
```

### Verificar instalación

```bash
# Health check
curl http://localhost:8000/health

# Documentación interactiva
open http://localhost:8000/docs
```

---

## 📚 API Endpoints

### Auditoría Legal (UC-01)

```bash
POST /api/v1/audit/land-use
```

Verifica si un terreno tiene restricciones por incendios.

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

### Certificados (UC-07)

```bash
# Emitir certificado
POST /api/v1/certificates/issue

# Descargar PDF
GET /api/v1/certificates/download/{certificate_number}

# Verificar autenticidad
GET /api/v1/certificates/verify/{certificate_number}
```

---

## 🏗️ Arquitectura

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Frontend      │────▶│   FastAPI       │────▶│   Supabase      │
│   (React)       │     │   (Python)      │     │   (PostgreSQL)  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌─────────────────┐
                        │   NASA FIRMS    │
                        │   (Datos)       │
                        └─────────────────┘
```

### Stack Tecnológico

| Componente | Tecnología |
|------------|------------|
| API | FastAPI + Uvicorn |
| Base de Datos | PostgreSQL + PostGIS (Supabase) |
| ORM | SQLAlchemy + GeoAlchemy2 |
| PDFs | FPDF2 + QRCode |
| Deploy | Render / Docker |

---

## 📁 Estructura del Proyecto

```
forestguard/
├── app/
│   ├── api/
│   │   ├── routes/
│   │   │   ├── audit.py        # UC-01: Auditoría
│   │   │   ├── certificates.py # UC-07: Certificados
│   │   │   └── fires.py        # CRUD incendios
│   │   └── deps.py             # Dependencias
│   ├── core/
│   │   ├── config.py           # Configuración
│   │   └── logging.py          # Logging
│   ├── models/                 # SQLAlchemy models
│   ├── schemas/                # Pydantic schemas
│   ├── services/               # Lógica de negocio
│   └── main.py                 # Entry point
├── scripts/
│   ├── load_firms_incremental.py  # Carga diaria FIRMS
│   ├── cluster_fire_events.py     # Clustering
│   └── cross_fire_protected_areas.py  # Cruce legal
├── Dockerfile
├── render.yaml
├── requirements.txt
└── README.md
```

---

## 🔧 Configuración

### Variables de Entorno

```bash
# Base de datos (Supabase)
DB_HOST=db.xxxx.supabase.co
DB_PORT=5432
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=tu_password

# Aplicación
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=tu_clave_secreta

# NASA FIRMS (para actualizaciones)
FIRMS_API_KEY=tu_api_key
```

### Obtener API Key de NASA FIRMS

1. Ir a https://firms.modaps.eosdis.nasa.gov/api/area/
2. Registrarse (gratis)
3. Copiar el API key

---

## 🚢 Deploy

### Oracle Cloud

1. Crear cuenta en [Render](https://render.com)
2. Conectar repositorio de GitHub
3. Crear nuevo "Web Service"
4. Seleccionar "Docker"
5. Configurar variables de entorno
6. Deploy automático ✅

### Docker Manual

```bash
# Build
docker build -t forestguard-api .

# Run
docker run -p 8000:8000 --env-file .env forestguard-api
```

---

## 📊 Scripts de Datos

### Carga Incremental Diaria

```bash
# Descargar últimos 2 días de FIRMS
python scripts/load_firms_incremental.py

# O especificar días
python scripts/load_firms_incremental.py --days 3
```

### Clustering de Eventos

```bash
# Procesar rango de fechas
python scripts/cluster_fire_events_parallel.py \
  --start-date 2024-01-01 \
  --end-date 2024-12-31
```

### Cruce con Áreas Protegidas

```bash
# Batch completo (primera vez)
python scripts/cross_fire_protected_areas.py --mode batch

# Incremental (diario)
python scripts/cross_fire_protected_areas.py --mode incremental
```

---

## 📜 Marco Legal

### Ley 26.815 Art. 22 bis

| Tipo de Zona | Prohibición |
|--------------|-------------|
| Bosques nativos | 60 años |
| Áreas protegidas | 60 años |
| Zonas agrícolas | 30 años |

La prohibición impide:
- Cambio de uso del suelo
- Loteo inmobiliario
- Construcción
- Agricultura intensiva

---

## 🧪 Testing

```bash
# Ejecutar tests
pytest

# Con coverage
pytest --cov=app --cov-report=html
```

---

## 📈 Roadmap

- [x] **MVP Core**
  - [x] Carga de datos FIRMS (2015-2025)
  - [x] Clustering de eventos
  - [x] Cruce con áreas protegidas
  - [x] Endpoint de auditoría
  - [x] Generación de certificados PDF

- [ ] **Pre-Frontend**
  - [ ] Datos climáticos (Open-Meteo)
  - [ ] Monitoreo NDVI
  - [ ] Denuncias ciudadanas (UC-09)

- [ ] **Frontend**
  - [ ] Dashboard React + Leaflet
  - [ ] Formularios de consulta
  - [ ] Mapa interactivo

---

## 🤝 Contribuir

1. Fork el repositorio
2. Crear branch (`git checkout -b feature/nueva-funcionalidad`)
3. Commit cambios (`git commit -am 'Agregar nueva funcionalidad'`)
4. Push al branch (`git push origin feature/nueva-funcionalidad`)
5. Crear Pull Request

---

## 📄 Licencia

MIT License - Ver [LICENSE](LICENSE) para detalles.

---

## 👨‍💻 Autor

**Nicolás Gabriel Hruszczak** - Analista Funcional

---

## 🙏 Agradecimientos

- **NASA FIRMS** - Datos de detección de incendios
- **Supabase** - Base de datos PostgreSQL
- **FastAPI** - Framework web


## 🤝 Contacto y Contribuciones
Este es un proyecto de código abierto desarrollado para proteger el patrimonio natural argentino.

**Última actualización:** Enero 2025  
**Versión:** 1.0.0
