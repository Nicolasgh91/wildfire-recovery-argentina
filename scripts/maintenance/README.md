# Scripts Esenciales de Mantenimiento - ForestGuard

Estos scripts son críticos para el funcionamiento continuo de ForestGuard en producción.

## Scripts Críticos

### 1. `run_migration.py`
**Propósito**: Aplicar migraciones de base de datos
**Uso**: 
```bash
# Aplicar todas las migraciones pendientes
python scripts/maintenance/run_migration.py

# Verificar estado actual
python scripts/maintenance/run_migration.py --check
```
**Cuándo ejecutar**: 
- Durante deployment inicial
- Después de actualizaciones que incluyan cambios en DB

### 2. `load_firms_incremental.py`
**Propósito**: Descargar datos diarios de NASA FIRMS
**Uso**:
```bash
# Cargar datos del día anterior
python scripts/maintenance/load_firms_incremental.py --days-back 1

# Cargar últimos 3 días
python scripts/maintenance/load_firms_incremental.py --days-back 3
```
**Cuándo ejecutar**: 
- Diario vía cron (recomendado: 6 AM UTC-3)
- Manualmente si faltan datos recientes

### 3. `aggregate_fire_episodes.py`
**Propósito**: Agrupar eventos de incendios en episodios para optimizar GEE
**Uso**:
```bash
# Procesar episodios activos
python scripts/maintenance/aggregate_fire_episodes.py

# Incluir eventos cerrados recientes
python scripts/maintenance/aggregate_fire_episodes.py --input-status active+closed
```
**Cuándo ejecutar**:
- Diario después de cargar datos FIRMS
- Antes de procesar imágenes satelitales

### 4. `run_carousel_local.py`
**Propósito**: Generar carrusel de imágenes satelitales
**Uso**:
```bash
# Procesar incendios activos
python scripts/maintenance/run_carousel_local.py --mode active

# Procesar históricos recientes
python scripts/maintenance/run_carousel_local.py --mode historic
```
**Cuándo ejecutar**:
- Diario (recomendado: 2 PM UTC-3)
- Después de aggregate_fire_episodes.py

## Configuración Cron Recomendada

```bash
# Editar crontab
crontab -e

# Agregar tareas diarias
0 6 * * * cd /opt/forestguard && source venv/bin/activate && python scripts/maintenance/load_firms_incremental.py --days-back 1 >> /var/log/forestguard/firms_incremental.log 2>&1

0 7 * * * cd /opt/forestguard && source venv/bin/activate && python scripts/maintenance/aggregate_fire_episodes.py >> /var/log/forestguard/episodes.log 2>&1

0 14 * * * cd /opt/forestguard && source venv/bin/activate && python scripts/maintenance/run_carousel_local.py >> /var/log/forestguard/satellite_slides.log 2>&1
```

## Variables de Entorno Requeridas

Todos los scripts requieren las siguientes variables de entorno:
- `DATABASE_URL` - Conexión a PostgreSQL
- `FIRMS_API_KEY` - API key de NASA FIRMS
- `GEE_SERVICE_ACCOUNT_JSON` - Credenciales Google Earth Engine
- `GCS_PROJECT_ID` - Proyecto Google Cloud Storage

## Verificación de Funcionamiento

### 1. Verificar carga de datos FIRMS
```sql
-- Verificar datos del día anterior
SELECT COUNT(*) FROM fire_detections 
WHERE acquisition_date >= CURRENT_DATE - INTERVAL '1 day';
```

### 2. Verificar episodios
```sql
-- Verificar episodios actualizados
SELECT COUNT(*) FROM fire_episodes 
WHERE updated_at >= CURRENT_DATE - INTERVAL '1 day';
```

### 3. Verificar carrusel
```sql
-- Verificar imágenes procesadas
SELECT COUNT(*) FROM fire_events 
WHERE last_update_sat >= CURRENT_DATE - INTERVAL '1 day';
```

## Troubleshooting

### Error: "No se puede conectar a la base de datos"
- Verificar `DATABASE_URL` en `.env`
- Confirmar que PostgreSQL está corriendo
- Revisar firewall y conectividad

### Error: "FIRMS API rate limit exceeded"
- NASA FIRMS tiene límite de 1000 requests/hora
- Esperar y reintentar más tarde
- Considerar usar MAP_KEY para mayor límite

### Error: "GEE quota exceeded"
- Google Earth Engine tiene límite diario
- Revisar cuota en GEE Console
- Optimizar parámetros de procesamiento

## Logs y Monitoreo

Los scripts generan logs en:
- `/var/log/forestguard/firms_incremental.log`
- `/var/log/forestguard/episodes.log`
- `/var/log/forestguard/satellite_slides.log`

Configurar monitoreo para:
- Tasa de éxito > 95%
- Tiempo de ejecución < 30 minutos
- Sin errores críticos

## Backup y Recuperación

Antes de ejecutar scripts:
- Hacer backup de base de datos (Supabase lo hace automáticamente)
- Documentar versión actual de migraciones
- Tener rollback plan disponible

Para recuperación:
- Restaurar desde backup point-in-time de Supabase
- Re-ejecutar migraciones si es necesario
- Verificar integridad de datos post-recuperación
