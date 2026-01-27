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

### 3️⃣ `cluster_fire_events.py` - Agrupación de Eventos

**Qué hace:**
- Agrupa detecciones cercanas en eventos únicos
- Usa algoritmo DBSCAN (clustering espacial)
- Calcula estadísticas: FRP promedio, duración, etc.
- Crea registros en `fire_events`

**Uso básico:**

```bash
# Procesar un día específico
python scripts/cluster_fire_events.py \
    --date 2024-08-15 \
    --database-url $DATABASE_URL

# Procesar un rango de fechas
python scripts/cluster_fire_events.py \
    --start-date 2024-01-01 \
    --end-date 2024-12-31 \
    --database-url $DATABASE_URL

# Personalizar parámetros de clustering
python scripts/cluster_fire_events.py \
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

## 🚀 Workflow Completo de Carga Inicial

### Paso 1: Preparar entorno

```bash
# Crear directorios
mkdir -p data/raw/firms
mkdir -p data/raw/protected_areas

# Activar entorno virtual
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

### Paso 2: Configurar base de datos

```bash
# Exportar URL de base de datos
export DATABASE_URL="postgresql://user:password@localhost:5432/wildfire_db"

# Aplicar migraciones (crear tablas)
alembic upgrade head

# Verificar que las tablas existen
psql $DATABASE_URL -c "\dt"
```

### Paso 3: Cargar datos satelitales (2024-2025)

```bash
# VIIRS 2024 (más preciso)
python scripts/load_firms_history.py \
    --year 2024 \
    --satellite VIIRS \
    --database-url $DATABASE_URL

# VIIRS 2025 (año actual)
python scripts/load_firms_history.py \
    --year 2025 \
    --satellite VIIRS \
    --database-url $DATABASE_URL

# Verificar carga
psql $DATABASE_URL -c "SELECT COUNT(*) FROM fire_detections;"
```

**Resultado esperado:** ~20,000-30,000 registros

### Paso 4: Cargar áreas protegidas

```bash
# Descargar shapefile de Parques Nacionales
# (Asume que ya lo tienes en data/raw/)

python scripts/load_protected_areas.py \
    --shapefile data/raw/parques_nacionales.shp \
    --category national_park \
    --jurisdiction national \
    --prohibition-years 60 \
    --database-url $DATABASE_URL

# Verificar carga
psql $DATABASE_URL -c "SELECT COUNT(*), category FROM protected_areas GROUP BY category;"
```

**Resultado esperado:** ~40-50 áreas protegidas nacionales

### Paso 5: Generar eventos (clustering)

```bash
# Procesar todo 2024
python scripts/cluster_fire_events.py \
    --start-date 2024-01-01 \
    --end-date 2024-12-31 \
    --database-url $DATABASE_URL

# Procesar 2025 hasta hoy
python scripts/cluster_fire_events.py \
    --start-date 2025-01-01 \
    --end-date 2025-01-24 \
    --database-url $DATABASE_URL

# Verificar eventos creados
psql $DATABASE_URL -c "SELECT COUNT(*) FROM fire_events;"
```

**Resultado esperado:** ~5,000-8,000 eventos únicos

---

## 📊 Validación de Datos Cargados

### Queries de Verificación

```sql
-- 1. Resumen de detecciones por satélite
SELECT 
    satellite,
    COUNT(*) as total,
    MIN(acquisition_date) as first_date,
    MAX(acquisition_date) as last_date
FROM fire_detections
GROUP BY satellite;

-- 2. Eventos creados por mes
SELECT 
    DATE_TRUNC('month', start_date) as month,
    COUNT(*) as events,
    AVG(total_detections) as avg_detections_per_event
FROM fire_events
GROUP BY month
ORDER BY month DESC;

-- 3. Áreas protegidas por provincia
SELECT 
    province,
    COUNT(*) as areas,
    SUM(area_hectares) as total_hectares
FROM protected_areas
GROUP BY province
ORDER BY total_hectares DESC;

-- 4. Top 10 incendios más intensos
SELECT 
    id,
    start_date,
    max_frp,
    total_detections,
    province
FROM fire_events
ORDER BY max_frp DESC NULLS LAST
LIMIT 10;

-- 5. Verificar que los índices espaciales funcionan
EXPLAIN ANALYZE
SELECT COUNT(*) FROM fire_events
WHERE ST_DWithin(
    centroid,
    ST_SetSRID(ST_MakePoint(-58.3816, -34.6037), 4326),
    5000
);
-- Debe usar "Index Scan using idx_fire_events_centroid"
```

---

## 🐛 Troubleshooting

### Error: "ModuleNotFoundError: No module named 'geopandas'"

```bash
# Instalar dependencias geoespaciales
pip install geopandas shapely fiona
```

### Error: "GEOS geometry operation error"

```bash
# Instalar librerías GEOS en el sistema
# Ubuntu/Debian:
sudo apt-get install libgeos-dev

# macOS:
brew install geos
```

### Error: "Connection refused" al conectar a PostgreSQL

```bash
# Verificar que PostgreSQL está corriendo
sudo systemctl status postgresql

# Verificar que PostGIS está instalado
psql $DATABASE_URL -c "SELECT PostGIS_version();"
```

### Performance lenta al insertar

**Síntoma:** Inserción de 10,000 registros tarda > 5 minutos

**Solución:**
```sql
-- Desactivar índices temporalmente durante carga masiva
DROP INDEX idx_fire_detections_location;
DROP INDEX idx_fire_detections_date;

-- Cargar datos...

-- Recrear índices
CREATE INDEX idx_fire_detections_location ON fire_detections USING GIST(location);
CREATE INDEX idx_fire_detections_date ON fire_detections(acquisition_date DESC);
```

---

## 🔄 Actualización Incremental (Cron Jobs)

Para mantener los datos actualizados automáticamente:

```bash
# Archivo: scripts/update_daily.sh

#!/bin/bash
set -e

export DATABASE_URL="postgresql://user:password@localhost:5432/wildfire_db"

# Descargar datos de ayer
YESTERDAY=$(date -d "yesterday" +%Y-%m-%d)

echo "Actualizando datos para $YESTERDAY"

# Nota: NASA FIRMS no tiene endpoint para día específico en bulk
# Necesitas usar la API transaccional (requiere MAP_KEY)

# Procesar clustering del día anterior
python scripts/cluster_fire_events.py \
    --date $YESTERDAY \
    --database-url $DATABASE_URL

echo "✅ Actualización completa"
```

**Configurar cron:**

```bash
# Ejecutar todos los días a las 6 AM
crontab -e

# Agregar línea:
0 6 * * * /path/to/scripts/update_daily.sh >> /var/log/wildfire_update.log 2>&1
```

---

## 📈 Métricas de Performance

| Script | Datos Procesados | Tiempo Promedio | RAM Requerida |
|--------|------------------|-----------------|---------------|
| `load_firms_history` | 20,000 detecciones | 10 min | 500 MB |
| `load_protected_areas` | 50 áreas | 2 min | 200 MB |
| `cluster_fire_events` | 365 días | 60 min | 1 GB |

**Hardware recomendado:**
- CPU: 2+ cores
- RAM: 4 GB mínimo
- Disco: 10 GB libre (datos + cache)
- Red: 10 Mbps (para descarga de CSVs)

---

## ✅ Checklist de Carga Inicial Completa

- [ ] Base de datos PostgreSQL + PostGIS configurada
- [ ] Tablas creadas (ejecutar `alembic upgrade head`)
- [ ] Descargados datos FIRMS 2024
- [ ] Descargados datos FIRMS 2025
- [ ] Cargadas detecciones en `fire_detections`
- [ ] Descargados shapefiles de áreas protegidas
- [ ] Cargadas áreas en `protected_areas`
- [ ] Ejecutado clustering para generar `fire_events`
- [ ] Verificadas queries espaciales (ST_DWithin funciona)
- [ ] Índices creados y funcionando
- [ ] Scripts de validación ejecutados sin errores

**Cuando todos los ítems estén ✅, tu base de datos estará lista para la API.** 🎉

---

**¿Necesitás ayuda?** Abrí un issue en GitHub o contactá al equipo.