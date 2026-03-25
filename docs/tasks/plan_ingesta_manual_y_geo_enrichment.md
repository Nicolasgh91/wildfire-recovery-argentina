# Plan técnico: ingesta manual FIRMS y enriquecimiento geográfico

Fecha: 2026-03-25
Estado: pendiente de validación

---

## Contexto y diagnóstico

Se detectaron dos gaps en el pipeline actual:

1. **Episodios sin provincia**: el clustering crea `fire_events` sin asignar `province`/`department`. La task `geo_enrichment` existe en las colas del `worker-gee` pero no está integrada como paso del pipeline. La tabla `regions` (con geometrías de provincias/departamentos) ya existe en la BD.
2. **Sin mecanismo de ingesta manual**: no hay endpoint para subir un CSV descargado de NASA FIRMS y ejecutar la cadena completa.

### Decisiones tomadas

- D-01: el enriquecimiento geográfico se integra al clustering (no como batch periódico separado).
- D-02: la carga manual se hace vía CSV descargado desde la web de FIRMS.
- D-03: se crea un endpoint API admin `POST /api/v1/admin/ingest-firms` con upload CSV.

---

## Roadmap de fases

```
Fase 1 ──── Schema + función SQL de geocodificación     [no requiere deploy]
Fase 2 ──── Worker: integrar geocodificación al clustering
Fase 3 ──── Worker: ingesta manual desde CSV
Fase 4 ──── API: endpoint admin de upload + cadena completa
Fase 5 ──── Corrección histórica (backfill) + propagación a episodios
Fase 6 ──── Verificación end-to-end
```

---

## Fase 1: schema y función SQL de geocodificación

Jerarquía: **schema**

### F1-T01: crear función SQL `assign_province_department`

**Archivo**: `database/functions/assign_province_department.sql`

**Estado de ejecución**: función creada y ejecutada en Supabase; validación inicial reportó `province='Córdoba'` y `department=NULL` para punto Córdoba centro. Se incorpora hardening por SRID y estrategia espacial con fallback.

```sql
CREATE OR REPLACE FUNCTION public.assign_province_department(
    p_centroid GEOGRAPHY
)
RETURNS TABLE (province VARCHAR, department VARCHAR)
LANGUAGE sql
STABLE
AS $$
    WITH point_input AS (
        SELECT ST_Transform(
            ST_SetSRID(
                p_centroid::geometry,
                COALESCE(NULLIF(ST_SRID(p_centroid::geometry), 0), 4326)
            ),
            4326
        ) AS point_geom
    ),
    regions_normalized AS (
        SELECT
            r.id,
            r.name,
            r.category,
            CASE
                WHEN ST_SRID(r.geom::geometry) = 4326 THEN r.geom::geometry
                WHEN ST_SRID(r.geom::geometry) = 0 THEN ST_SetSRID(r.geom::geometry, 4326)
                ELSE ST_Transform(r.geom::geometry, 4326)
            END AS geom_4326
        FROM public.regions r
        WHERE r.category IN ('PROVINCIA', 'DEPARTAMENTO')
    ),
    province_pick AS (
        SELECT candidate.name
        FROM (
            SELECT r.name, 1 AS priority, ST_Distance(r.geom_4326, p.point_geom) AS dist, r.id
            FROM regions_normalized r
            CROSS JOIN point_input p
            WHERE r.category = 'PROVINCIA' AND ST_Covers(r.geom_4326, p.point_geom)
            UNION ALL
            SELECT r.name, 2 AS priority, ST_Distance(r.geom_4326, p.point_geom) AS dist, r.id
            FROM regions_normalized r
            CROSS JOIN point_input p
            WHERE r.category = 'PROVINCIA' AND ST_Intersects(r.geom_4326, p.point_geom)
        ) AS candidate
        ORDER BY candidate.priority, candidate.dist, candidate.id
        LIMIT 1
    ),
    department_pick AS (
        SELECT candidate.name
        FROM (
            SELECT r.name, 1 AS priority, ST_Distance(r.geom_4326, p.point_geom) AS dist, r.id
            FROM regions_normalized r
            CROSS JOIN point_input p
            WHERE r.category = 'DEPARTAMENTO' AND ST_Covers(r.geom_4326, p.point_geom)
            UNION ALL
            SELECT r.name, 2 AS priority, ST_Distance(r.geom_4326, p.point_geom) AS dist, r.id
            FROM regions_normalized r
            CROSS JOIN point_input p
            WHERE r.category = 'DEPARTAMENTO' AND ST_Intersects(r.geom_4326, p.point_geom)
        ) AS candidate
        ORDER BY candidate.priority, candidate.dist, candidate.id
        LIMIT 1
    )
    SELECT p.name AS province, d.name AS department
    FROM province_pick p
    LEFT JOIN department_pick d ON TRUE;
$$;
```

**Justificación**: función reutilizable desde el worker de clustering y desde el backfill. Se evita el join cruzado provincia/departamento y se normaliza SRID a 4326 para evitar falsos `NULL` cuando `regions.geom` viene con SRID 0 o distinto. La estrategia `ST_Covers` + fallback `ST_Intersects` mejora precisión en casos de borde.

**Verificación**:
```sql
-- Diagnóstico de metadata espacial (SRID trap)
SELECT f_geometry_column, srid, type
FROM geometry_columns
WHERE f_table_name = 'regions';

-- Test con un centroide conocido (ej. centro de Córdoba)
SELECT * FROM assign_province_department(
    ST_SetSRID(ST_MakePoint(-64.18, -31.42), 4326)::geography
);
-- Esperado: province = 'Córdoba', department = 'Capital'

-- Punto borde aproximado Córdoba/Santa Fe
SELECT * FROM assign_province_department(
    ST_SetSRID(ST_MakePoint(-62.0, -32.0), 4326)::geography
);

-- Punto control austral (Patagonia sur)
SELECT * FROM assign_province_department(
    ST_SetSRID(ST_MakePoint(-68.3, -54.8), 4326)::geography
);
```

### F1-T02: verificar índice espacial en `regions`

**Archivo**: `database/migrations/check_regions_spatial_index.sql`

```sql
-- Verificar si existe
SELECT indexname FROM pg_indexes
WHERE tablename = 'regions' AND indexdef LIKE '%gist%';

-- Si no existe, crear:
CREATE INDEX IF NOT EXISTS idx_regions_geom_gist
ON public.regions USING GIST (geom);
```

**Criterio de aceptación**: el `EXPLAIN` de `assign_province_department` muestra uso del índice GiST, y los puntos de Córdoba/frontera/Patagonia devuelven resultado consistente según cobertura real de `regions`.

---

## Fase 2: integrar geocodificación al clustering

Jerarquía: **flow logic → workers**

### F2-T01: modificar `cluster_detections` para asignar provincia

**Archivo**: `workers/tasks/clustering.py` (función que crea `fire_events`)

**Cambio**: después de calcular el centroide del cluster y antes de `INSERT INTO fire_events`, ejecutar:

```python
# Pseudocódigo del cambio quirúrgico
# Dentro del loop que crea fire_events por cada cluster:

result = session.execute(
    text("""
        SELECT province, department
        FROM assign_province_department(
            ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
        )
    """),
    {"lon": centroid_lon, "lat": centroid_lat}
).fetchone()

fire_event.province = result.province if result else None
fire_event.department = result.department if result else None
```

**Reglas de ejecución para el agente**:
- NO modificar la lógica de clustering (DBSCAN/ST-DBSCAN).
- NO modificar el cálculo de centroide ni métricas.
- Solo agregar la asignación de `province`/`department` después de calcular el centroide.
- Si `assign_province_department` no devuelve resultado (centroide fuera de Argentina), dejar `NULL` y loguear warning.
- El cambio debe ser idempotente: si el evento ya tiene provincia asignada, no sobreescribir.

**Verificación**:
```bash
# Ejecutar clustering manual sobre detecciones recientes
docker exec -it forestguard-worker-fast \
  celery -A workers.celery_app call \
  workers.tasks.clustering.cluster_detections \
  --kwargs='{"days_back": 7}'

# Verificar que los nuevos eventos tienen provincia
docker exec forestguard-api python -c "
from app.db.session import SessionLocal
from sqlalchemy import text
db = SessionLocal()
r = db.execute(text(\"\"\"
    SELECT province, COUNT(*)
    FROM fire_events
    WHERE created_at > NOW() - INTERVAL '1 hour'
    GROUP BY province
\"\"\")).fetchall()
print(r)
db.close()
"
```

### F2-T02: modificar `cluster_fire_episodes_pipeline` para propagar provincias

**Archivo**: `workers/tasks/clustering_task.py`

**Cambio**: al crear/actualizar `fire_episodes`, poblar el campo `provinces` (ARRAY) desde los `fire_events` vinculados:

```python
# Pseudocódigo: después de vincular eventos al episodio
provinces = session.execute(
    text("""
        SELECT ARRAY_AGG(DISTINCT fe.province)
        FILTER (WHERE fe.province IS NOT NULL)
        FROM fire_episode_events fee
        JOIN fire_events fe ON fe.id = fee.event_id
        WHERE fee.episode_id = :episode_id
    """),
    {"episode_id": str(episode.id)}
).scalar()

episode.provinces = provinces or []
```

**Reglas de ejecución para el agente**:
- Aplicar en el punto donde se actualizan las métricas agregadas del episodio (`event_count`, `detection_count`, etc.).
- No modificar la lógica de merge de episodios.

---

## Fase 3: ingesta manual desde CSV

Jerarquía: **workers**

### F3-T01: crear task `ingest_firms_csv`

**Archivo**: `workers/tasks/ingestion.py`

**Función**: nueva task Celery que recibe la ruta de un archivo CSV ya guardado en el filesystem del contenedor y ejecuta la misma lógica que `download_firms_daily` pero desde archivo local.

```python
@celery_app.task(bind=True, queue='ingestion', max_retries=1)
def ingest_firms_csv(self, csv_path: str, source_label: str = 'manual_upload'):
    """Ingesta detecciones desde un CSV local de NASA FIRMS.

    Args:
        csv_path: ruta absoluta al CSV en el filesystem del contenedor.
        source_label: etiqueta para logging y trazabilidad.

    Returns:
        dict con 'new_detections', 'duplicates', 'errors'.
    """
```

**Requisitos**:
- Reutilizar la lógica de parseo existente en `download_firms_daily` (columnas FIRMS: latitude, longitude, brightness, scan, track, acq_date, acq_time, satellite, instrument, confidence, version, bright_t31, frp, daynight, type).
- Calcular `h3_index`, construir `detected_at` como timestamptz, deduplicar por llave compuesta.
- Marcar `is_processed=false`, `fire_event_id=null`.
- Loguear: total de filas, insertadas, duplicadas, errores.
- Al finalizar, disparar encadenamiento automático (ver F3-T02).

**Formato CSV esperado de FIRMS** (columnas mínimas):
```
latitude,longitude,brightness,scan,track,acq_date,acq_time,satellite,instrument,confidence,version,bright_t31,frp,daynight,type
```

### F3-T02: crear task `run_full_ingestion_pipeline`

**Archivo**: `workers/tasks/ingestion.py`

**Función**: task orquestadora que ejecuta la cadena completa en secuencia.

```python
@celery_app.task(bind=True, queue='ingestion')
def run_full_ingestion_pipeline(self, csv_path: str, source_label: str = 'manual_upload'):
    """Ejecuta la cadena completa: ingesta → clustering → episodios.

    Usa chain de Celery para secuencialidad.
    """
    from celery import chain

    pipeline = chain(
        ingest_firms_csv.si(csv_path, source_label),
        cluster_detections.si(days_back=30),  # 30 días para capturar el rango del CSV
        cluster_fire_episodes_pipeline.si(),
    )
    result = pipeline.apply_async()
    return {'pipeline_id': result.id}
```

**Nota**: el `days_back=30` es un valor seguro para capturar detecciones recientes. Si el CSV contiene datos más antiguos, se puede parametrizar.

---

## Fase 4: endpoint API admin de upload

Jerarquía: **API**

### F4-T01: crear endpoint `POST /api/v1/admin/ingest-firms`

**Archivo**: `app/api/routes/admin.py` (crear si no existe, o agregar al router admin existente)

```python
@router.post("/admin/ingest-firms", status_code=202)
async def upload_firms_csv(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """Sube un CSV de NASA FIRMS y ejecuta la cadena completa de ingesta.

    Requiere: admin autenticado.
    Acepta: archivo .csv, máximo 50 MB.
    Responde: 202 con task_id para polling.
    """
```

**Validaciones**:
- Solo admin (`current_user.role == 'admin'`).
- Extension `.csv` y content-type `text/csv` o `application/octet-stream`.
- Tamaño máximo: 50 MB (configurable vía `system_parameters`).
- Validar que el CSV tiene las columnas mínimas de FIRMS antes de encolar.
- Rate limit: máximo 1 ingesta manual cada 10 minutos.

**Flujo**:
1. Recibir archivo vía `UploadFile`.
2. Guardar en ruta temporal: `/tmp/firms_uploads/{uuid}_{original_name}.csv`.
3. Validar headers del CSV (columnas FIRMS esperadas).
4. Encolar `run_full_ingestion_pipeline.delay(csv_path, source_label='admin_upload')`.
5. Retornar `202 Accepted` con `{"task_id": "...", "status": "queued"}`.

### F4-T02: endpoint de estado de ingesta

**Archivo**: `app/api/routes/admin.py`

```python
@router.get("/admin/ingest-firms/{task_id}")
async def get_ingestion_status(
    task_id: str,
    current_user: User = Depends(get_current_user),
):
    """Consulta el estado de una ingesta manual por task_id."""
```

**Respuesta**: estado Celery (`PENDING`, `STARTED`, `SUCCESS`, `FAILURE`) + resultado si completó.

### F4-T03: registrar router admin en `main.py`

**Archivo**: `app/main.py`

```python
from app.api.routes.admin import router as admin_router

app.include_router(
    admin_router,
    prefix="/api/v1",
    tags=["admin"],
    dependencies=[Depends(get_current_user)],
)
```

---

## Fase 5: corrección histórica (backfill) + propagación

Jerarquía: **workers**

### F5-T01: script SQL de backfill para `fire_events` sin provincia

**Archivo**: `database/scripts/backfill_provinces.sql`

```sql
-- Backfill fire_events que tienen centroide pero no provincia
UPDATE fire_events fe
SET
    province = geo.province,
    department = geo.department,
    updated_at = NOW()
FROM (
    SELECT
        fe2.id,
        apd.province,
        apd.department
    FROM fire_events fe2
    CROSS JOIN LATERAL assign_province_department(fe2.centroid) apd
    WHERE fe2.province IS NULL
        AND fe2.centroid IS NOT NULL
) geo
WHERE fe.id = geo.id;
```

**Ejecución**: manual, una sola vez, después de verificar F1-T01 y F2-T01.

**Verificación pre-backfill**:
```sql
SELECT COUNT(*) AS sin_provincia
FROM fire_events
WHERE province IS NULL AND centroid IS NOT NULL;
```

**Verificación post-backfill**:
```sql
SELECT province, COUNT(*) AS total
FROM fire_events
WHERE province IS NOT NULL
GROUP BY province
ORDER BY total DESC;
```

### F5-T02: propagar provincias a episodios existentes

**Archivo**: `database/scripts/backfill_episode_provinces.sql`

```sql
UPDATE fire_episodes ep
SET
    provinces = sub.province_list,
    updated_at = NOW()
FROM (
    SELECT
        fee.episode_id,
        ARRAY_AGG(DISTINCT fe.province)
            FILTER (WHERE fe.province IS NOT NULL) AS province_list
    FROM fire_episode_events fee
    JOIN fire_events fe ON fe.id = fee.event_id
    GROUP BY fee.episode_id
) sub
WHERE ep.id = sub.episode_id
    AND (ep.provinces IS NULL OR ep.provinces = '{}');
```

---

## Fase 6: verificación end-to-end

### F6-T01: test de flujo completo

**Procedimiento manual**:

1. Descargar CSV de prueba desde NASA FIRMS (últimas 24h, Argentina).
2. Subir vía `POST /api/v1/admin/ingest-firms`.
3. Verificar respuesta `202` con `task_id`.
4. Consultar `GET /api/v1/admin/ingest-firms/{task_id}` hasta `SUCCESS`.
5. Verificar en BD:
   - `fire_detections` nuevas con `is_processed=false` → luego `true`.
   - `fire_events` nuevos con `province` y `department` asignados.
   - `fire_episodes` actualizados con `provinces` array no vacío.
6. Verificar en UI: episodios nuevos muestran provincia correctamente.

### F6-T02: verificar backfill histórico

```sql
-- No debe haber eventos con centroide en Argentina sin provincia
SELECT COUNT(*) AS pendientes
FROM fire_events
WHERE province IS NULL
    AND centroid IS NOT NULL
    AND ST_Y(centroid::geometry) BETWEEN -56 AND -21
    AND ST_X(centroid::geometry) BETWEEN -74 AND -53;
-- Esperado: 0
```

---

## Resumen de archivos a crear/modificar

| Archivo | Acción | Fase |
|---------|--------|------|
| `database/functions/assign_province_department.sql` | Crear | F1 |
| `database/migrations/check_regions_spatial_index.sql` | Crear | F1 |
| `workers/tasks/clustering.py` | Modificar | F2 |
| `workers/tasks/clustering_task.py` | Modificar | F2 |
| `workers/tasks/ingestion.py` | Modificar (agregar 2 tasks) | F3 |
| `app/api/routes/admin.py` | Crear | F4 |
| `app/main.py` | Modificar (registrar router) | F4 |
| `database/scripts/backfill_provinces.sql` | Crear | F5 |
| `database/scripts/backfill_episode_provinces.sql` | Crear | F5 |

## Riesgos y mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|-------------|---------|------------|
| `regions` sin datos para alguna provincia | Baja | Medio | Verificar cobertura antes de backfill: `SELECT DISTINCT name FROM regions WHERE category='PROVINCIA'` |
| CSV de FIRMS con formato inesperado | Media | Bajo | Validar headers antes de encolar; rechazar con 422 si no matchean |
| Backfill lento en >100k eventos | Media | Bajo | Ejecutar en batches de 5000 con `LIMIT/OFFSET` o con `WHERE id > last_id` |
| Centroide en frontera entre provincias | Baja | Bajo | `LIMIT 1` en la función SQL; resultado determinístico por orden de `regions.id` |
| Tamaño del CSV excede memoria del worker | Baja | Medio | Parseo por streaming (csv.reader + batch inserts cada 1000 filas) |

## Dependencias entre fases

```
F1 ──→ F2 (clustering necesita la función SQL)
F1 ──→ F5 (backfill necesita la función SQL)
F3 ──→ F4 (API llama a la task de ingesta)
F2 + F3 ──→ F6 (verificación requiere ambos cambios)
```

F1 y F3 pueden ejecutarse en paralelo. F5 puede ejecutarse apenas F1 esté lista (no bloquea a F4).
