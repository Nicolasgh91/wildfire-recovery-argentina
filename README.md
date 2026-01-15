# 🔥 Sistema de Monitoreo de Recuperación Post-Incendios - Argentina

Sistema para detectar y monitorear la recuperación de terrenos afectados por incendios forestales en Argentina (2015-presente), utilizando análisis temporal de imágenes satelitales.

## 🎯 Problema que resuelve

Permite identificar incendios forestales históricos y evaluar la evolución del terreno durante los 3 años posteriores al evento, detectando:
- Rebrote de vegetación (mediante índice NDVI)
- Construcciones nuevas en zonas afectadas
- Incendios recurrentes en la misma área

## 🏗️ Arquitectura

```
┌─────────────┐
│   Usuario   │
└──────┬──────┘
       │
       ▼
┌─────────────────────┐      ┌──────────────────────┐
│   API Principal     │◄────►│   Base de Datos      │
│   (FastAPI)         │      │   (Supabase/PostGIS) │
│   Puerto: 8000      │      └──────────────────────┘
└──────┬──────────────┘
       │
       │ Delega análisis
       ▼
┌─────────────────────┐
│  Microservicio de   │
│  Análisis Imágenes  │
│  (FastAPI)          │
│  Puerto: 8001       │
└─────────────────────┘
       │
       ▼
┌─────────────────────┐
│  Google Earth       │
│  Engine API         │
│  (Sentinel-2)       │
└─────────────────────┘
```

## 📊 Casos de Uso Principales

### CU-01: Detectar incendios en región
**Actor:** Usuario  
**Flujo:**
1. Usuario especifica rango de fechas y provincia
2. Sistema consulta Google Earth Engine
3. Sistema identifica áreas con anomalías térmicas
4. Sistema guarda incendios en BD y marca incendios recurrentes

### CU-02: Analizar recuperación de incendio
**Actor:** Sistema (automático)  
**Flujo:**
1. Sistema obtiene imágenes mensuales (36 meses post-incendio)
2. Calcula índice NDVI para cada mes
3. Detecta cambios en construcciones
4. Guarda análisis temporal en BD

### CU-03: Consultar evolución de terreno
**Actor:** Usuario  
**Flujo:**
1. Usuario consulta incendio específico
2. Sistema retorna análisis temporal completo
3. Sistema alerta si hay superposición con otros incendios

## 🗂️ Estructura del Proyecto

```
wildfire-recovery-argentina/
├── api/                    # API REST principal
│   ├── main.py
│   ├── models.py
│   └── routes/
├── image-service/          # Microservicio de análisis
│   ├── main.py
│   ├── gee_client.py      # Google Earth Engine
│   └── analyzers/
├── database/
│   ├── schema.sql
│   └── migrations/
├── notebooks/              # Exploración de datos
└── docs/
    ├── arquitectura.md
    └── casos_de_uso.md
```

## 🚀 Instalación

```bash
# Clonar repositorio
git clone https://github.com/Nicolasgh91/wildfire-recovery-argentina.git
cd wildfire-recovery-argentina

# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales
```

## 🔧 Configuración

### Google Earth Engine
1. Registrarse en: https://earthengine.google.com/
2. Autenticar: `earthengine authenticate`

### Supabase
1. Crear proyecto en: https://supabase.com
2. Copiar URL y API Key al `.env`

## 📝 Reglas de Negocio

- **Incendio recurrente:** Mismo polígono (<100m) con 6+ meses de diferencia
- **Superposición significativa:** Áreas con >5% de solapamiento
- **Período de análisis:** 36 meses post-incendio (imágenes mensuales)
- **Resolución:** Sentinel-2 (10m) para detección de construcciones

## 🛠️ Tecnologías

- **Backend:** Python 3.14, FastAPI
- **Base de datos:** PostgreSQL + PostGIS (Supabase)
- **Imágenes satelitales:** Google Earth Engine (Sentinel-2)
- **Análisis:** NumPy, Rasterio, GDAL

## 📈 Roadmap

- [x] Definición de casos de uso
- [x] Diseño de arquitectura
- [ ] Detección de incendios históricos
- [ ] API REST - Consultas básicas
- [ ] Microservicio de análisis temporal
- [ ] Dashboard de visualización (futuro)

## 👨‍💻 Autor

**Nicolás Gabriel Hruszczak** - Analista Funcional  
Proyecto de portfolio para demostrar: APIs REST, Microservicios, Bases de datos, Supabase (free tier), Google Cloud

---

**Nota:** Este es un proyecto educativo sin fines comerciales. Uso gratuito de APIs bajo términos de servicio de Google Earth Engine y Supabase.
