# 🔧 Wildfire Recoveries - Scripts de Carga de Datos

## Resumen

Estos scripts cargan datos desde fuentes externas a la base de datos PostgreSQL/PostGIS.

---

## 📋 Scripts Disponibles

### 1️⃣ `load_firms_history.py` - NASA FIRMS

**Qué hace:**
- Descarga datos históricos de NASA FIRMS (VIIRS/MODIS)
- Filtra por Argentina (bounding box)
- Filtra por confianza >= 80%
- Inserta en `fire_detections`

**Uso básico:**

```bash
# Descargar VIIRS 2024
python scripts/load_firms_history.py \
    --year 2024 \
    --satellite VIIRS \
    --database-url $DATABASE_URL

# Descargar MODIS 2024
python scripts/load_firms_history.py \
    --year 2024 \
    --satellite MODIS \
    --database-url $DATABASE_URL

# Con umbral de confianza personalizado
python scripts/load_firms_history.py \
    --year 2024 \
    --satellite VIIRS \
    --confidence-threshold 90 \
    --database-url $DATABASE_URL
```

**Tiempo estimado:**
- Descarga: 5-10 minutos (dependiendo de conexión)
- Procesamiento: 2-5 minutos
- **Total: ~15 minutos** por año

**Datos generados:**
- 2024 VIIRS: ~10,000-15,000 detecciones (alta confianza)
- 2024 MODIS: ~8,000-12,000 detecciones

---

### 2️⃣ `load_protected_areas.py` - Áreas Protegidas

**Qué hace:**
- Lee shapefiles de áreas protegidas
- Simplifica geometrías (reduce vértices)
- Calcula centroides y áreas
- Inserta en `protected_areas`

**Dónde conseguir shapefiles:**

```bash
# Parques Nacionales de Argentina
wget https://datos.gob.ar/dataset/ambiente-parques-nacionales/archivo/ambiente_1.1

# Reservas Provinciales (ejemplo: Buenos Aires)
# Descargar desde: https://www.gba.gob.ar/desarrollo_agrario/datosabiertos
```

**Uso básico:**

```bash
# Cargar un shapefile individual
python scripts/load_protected_areas.py \
    --shapefile data/raw/parques_nacionales.shp \
    --category national_park \
    --jurisdiction national \
    --prohibition-years 60 \
    --database-url $DATABASE_URL

# Cargar múltiples shapefiles desde un directorio
python scripts/load_protected_areas.py \
    --directory data/raw/protected_areas/ \
    --category provincial_reserve \
    --jurisdiction provincial \
    --prohibition-years 30 \
    --database-url $DATABASE_URL
```

**Categorías disponibles:**
- `national_park` - Parque Nacional (60 años prohibición)
- `provincial_reserve` - Reserva Provincial (30 años)
- `natural_monument` - Monumento Natural (60 años)
- `biosphere_reserve` - Reserva de Biosfera (60 años)
- `ramsar_site` - Sitio Ramsar (60 años)

---

### 3️⃣ `cross_fire_protected_areas.py` - Intersecciones legales

**Qué hace:**
- Cruza `fire_events` con `protected_areas`
- Inserta en `fire_protected_area_intersections`
- Calcula `prohibition_until` según Ley 26.815

**Uso básico:**

```bash
# Procesamiento batch (recomendado para carga inicial)
python scripts/cross_fire_protected_areas.py --mode batch

# Procesamiento incremental (diario)
python scripts/cross_fire_protected_areas.py --mode incremental
```

---

### 4️⃣ `load_protected_area_pipeline.py` - Pipeline completo

**Qué hace:**
- Carga áreas protegidas desde IGN/APN
- Ejecuta el cruce con incendios para generar intersecciones

**Uso básico:**

```bash
# Pipeline completo desde IGN
python scripts/load_protected_area_pipeline.py --source ign --simplify 100 --truncate

# Pipeline incremental (sin truncar)
python scripts/load_protected_area_pipeline.py --source apn_wfs --simplify 50
```

---

### 5️⃣ `cluster_fire_events_parallel.py` - Agrupación de Eventos

**Qué hace:**
- Agrupa detecciones cercanas en eventos únicos
- Usa algoritmo DBSCAN (clustering espacial)
- Calcula estadísticas: FRP promedio, duración, etc.
- Crea registros en `fire_events`

**Uso básico:**

```bash
# Procesar un día específico
python scripts/cluster_fire_events_parallel.py \
    --date 2024-08-15 \
    --database-url $DATABASE_URL

# Procesar un rango de fechas
python scripts/cluster_fire_events_parallel.py \
    --start-date 2024-01-01 \
    --end-date 2024-12-31 \
    --database-url $DATABASE_URL

# Personalizar parámetros de clustering
python scripts/cluster_fire_events_parallel.py \
    --start-date 2024-08-01 \
    --end-date 2024-08-31 \
    --eps-meters 1000 \
    --min-samples 5 \
    --database-url $DATABASE_URL
```

**Parámetros de clustering:**
- `--eps-meters`: Radio de agrupación (default: 500m)
  - 500m: Estricto, eventos bien separados
  - 1000m: Más permisivo, agrupa incendios grandes
- `--min-samples`: Mínimo de detecciones (default: 3)
  - 3: Detecta eventos medianos
  - 1: Detecta todo, incluye incendios pequeños

**Tiempo estimado:**
- ~1 minuto por día con 100 detecciones
- **Total 2024: ~6 horas** (puede correrse overnight)

---

### 6) `process_satellite_slides.py` - Carruseles Satelitales (CU-15/CU-16)

**Qué hace:**
- Genera el carrusel satelital para incendios activos (CU-15).
- Genera el carrusel histórico "antes/después" para incendios extinguidos recientes (CU-16).
- Actualiza `slides_data`, `last_gee_image_id`, `last_update_sat` y `has_historic_report`.
- Por defecto procesa `fire_episodes` y aplica las slides a todos los eventos del episodio para reducir requests a GEE (usa `--use-events` para el modo legacy por evento).

**Uso básico:**

```bash
# Procesar activos + extinguidos recientes
python scripts/process_satellite_slides.py

# Solo activos
python scripts/process_satellite_slides.py --mode active

# Solo extinguidos (últimas 24h)
python scripts/process_satellite_slides.py --mode historic --days-back 1

# Limitar cantidad de incendios por corrida
python scripts/process_satellite_slides.py --max-fires 25

# Forzar modo legacy por evento (sin episodios)
python scripts/process_satellite_slides.py --use-events

# Incluir episodios no candidatos
python scripts/process_satellite_slides.py --episodes-all

# Ajustar padding del bbox de episodios (metros)
python scripts/process_satellite_slides.py --episode-bbox-padding-meters 3000

# Simular sin guardar en DB ni storage
python scripts/process_satellite_slides.py --dry-run
```

**Requisitos:**
- Credenciales GEE (GEE_SERVICE_ACCOUNT_JSON).
- Credenciales GCS (GCS_PROJECT_ID, GCS_SERVICE_ACCOUNT_JSON) y buckets de storage.

