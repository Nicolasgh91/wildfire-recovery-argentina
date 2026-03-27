# F1-BIS: carga de departamentos desde IGN/Georef

Fecha: 2026-03-25
Estado: completada
Bloquea: no (F2 y F5 desbloqueadas)
regions: DEPARTAMENTO=529, PROVINCIA=24.
Backfill histórico de fire_events finalizado (batch script).
---

## Contexto

El diagnóstico de F1-T01 confirmó que la tabla `regions` solo tiene registros con `category='PROVINCIA'`. No hay departamentos cargados, por lo que `assign_province_department` devuelve `department=NULL` para cualquier punto.

### Fuente de datos

API Georef de Argentina (datos.gob.ar): descarga completa de departamentos con geometrías.

- URL NDJSON (con geometrías): `https://apis.datos.gob.ar/georef/api/v2.0/departamentos.ndjson`
- URL GeoJSON (alternativa): `https://apis.datos.gob.ar/georef/api/v2.0/departamentos.geojson`
- SRID: EPSG:4326 (WGS84)
- Cantidad esperada: ~530 departamentos/partidos
- Licencia: datos abiertos del Estado argentino

### Estructura de cada registro NDJSON

```json
{
  "id": "06427",
  "nombre": "La Matanza",
  "nombre_completo": "Partido de la Matanza",
  "categoria": "Partido",
  "centroide": {"lat": -34.770165, "lon": -58.625449},
  "geometria": {"type": "MultiPolygon", "coordinates": [...]},
  "provincia": {"id": "06", "nombre": "Buenos Aires"},
  "fuente": "IGN"
}
```

**Nota**: `categoria` varía según la provincia: "Partido" (Buenos Aires), "Departamento" (mayoría), "Comuna" (CABA). Todos se insertan en `regions` con `category='DEPARTAMENTO'`.

---

## Tareas

### F1B-T01: carga principal con script Python (`psycopg2`)

**Archivo**: `database/scripts/load_departments_georef.py`

**Estrategia principal**: cargar `data/departments/departments.json` desde local y hacer inserts directos a `regions` con `DATABASE_URL` (sin credenciales hardcodeadas).

Comportamiento esperado del script:
1. Leer `DATABASE_URL` (fail-fast si falta).
2. Leer GeoJSON `FeatureCollection`.
3. Precheck de idempotencia:
   - si `COUNT(DEPARTAMENTO) >= 500`: abortar carga full.
   - si `COUNT(DEPARTAMENTO) = 0`: continuar carga full.
   - si `COUNT(DEPARTAMENTO)` entre 1 y 499: abortar por estado parcial.
4. Insertar en lotes (50) a `regions`:
   ```sql
   INSERT INTO public.regions (name, category, geom)
   VALUES (
     :nombre,
     'DEPARTAMENTO',
     ST_SetSRID(ST_Multi(ST_GeomFromGeoJSON(:geojson))::geometry, 4326)
   );
   ```
5. Reportar total leídos/insertados/errores.

Evidencia local del dataset cargable:
- archivo detectado: `data/departments/departments.json`
- features: `529`
- nombres nulos: `0`
- nombres únicos: `447` (esperable por homónimos entre provincias)

### F1B-T01-ALT: alternativa con `ogr2ogr`

`ogr2ogr` queda como alternativa operativa cuando GDAL está instalado en el entorno y se puede usar conexión segura a Supabase/PostGIS.

### F1B-T02: verificación post-carga

**Queries de verificación** (ejecutar en Supabase):

```sql
-- 1. Conteo por categoría (debe mostrar ~530 DEPARTAMENTO)
SELECT category, COUNT(*)
FROM regions
GROUP BY category
ORDER BY category;

-- 2. Cobertura: al menos un departamento por provincia
SELECT r_prov.name AS provincia, COUNT(r_dept.id) AS departamentos
FROM regions r_prov
LEFT JOIN regions r_dept
    ON r_dept.category = 'DEPARTAMENTO'
    AND ST_Intersects(r_dept.geom, r_prov.geom)
WHERE r_prov.category = 'PROVINCIA'
GROUP BY r_prov.name
ORDER BY departamentos ASC;

-- 3. Test puntual: Córdoba Capital
SELECT name, category
FROM regions
WHERE category = 'DEPARTAMENTO'
    AND ST_Intersects(geom, ST_SetSRID(ST_MakePoint(-64.18, -31.42), 4326));
-- Esperado: "Capital" (departamento de Córdoba)

-- 4. Test completo de la función
SELECT * FROM assign_province_department(
    ST_SetSRID(ST_MakePoint(-64.18, -31.42), 4326)::geography
);
-- Esperado: province='Córdoba', department='Capital'

-- 5. Test frontera Córdoba/Santa Fe
SELECT * FROM assign_province_department(
    ST_SetSRID(ST_MakePoint(-62.0, -32.0), 4326)::geography
);
-- Esperado: province y department no NULL

-- 6. Test Patagonia sur
SELECT * FROM assign_province_department(
    ST_SetSRID(ST_MakePoint(-69.0, -50.0), 4326)::geography
);
-- Esperado: province='Santa Cruz', department no NULL
```

**Go/No-Go para F2**:
- `COUNT(DEPARTAMENTO) >= 500` => OK
- provincias con `departamentos = 0` => FAIL
- cualquier punto de control con `department IS NULL` => FAIL

### F1B-T03: actualizar documentación

**Archivo**: `docs/tasks/plan_ingesta_manual_y_geo_enrichment.md`

Agregar:
- Estado F1-BIS: completada con evidencia.
- Fuente de datos de departamentos documentada.
- Conteo final de registros en `regions`.

---

## Ejecución recomendada

**Opción A (principal) — script Python con `DATABASE_URL`**:
```bash
DATABASE_URL="postgresql://..." python database/scripts/load_departments_georef.py
```

### Backfill histórico (incendios existentes)

Una vez que `regions` tenga `DEPARTAMENTO`, completar `department` en `fire_events` existentes en **batches** para evitar timeouts:

```bash
python database/scripts/backfill_fire_events_departments_batched.py --batch-size 100
```

El script:
- usa `.env` (y/o `DATABASE_URL`) sin hardcodear secretos,
- commitea por batch y loguea progreso (`pending`, `updated`, tiempo),
- detiene si no hay progreso (`updated=0`) o si `pending=0`.

**Opción B (fallback) — `ogr2ogr` a staging y promoción SQL**:
```bash
ogr2ogr -f "PostgreSQL" \
  PG:"host=... dbname=... user=... password=... sslmode=require" \
  departamentos.geojson \
  -nln public.regions_departments_staging \
  -nlt PROMOTE_TO_MULTI \
  -lco GEOMETRY_NAME=geom \
  -t_srs EPSG:4326 \
  -overwrite
```

---

## Criterio de aceptación para desbloquear F2

- `SELECT COUNT(*) FROM regions WHERE category='DEPARTAMENTO'` retorna >= 500.
- Los 3 puntos de control (Córdoba, frontera, Patagonia) devuelven province y department no NULL desde `assign_province_department`.
- No hay provincias sin al menos un departamento asociado.
- Backfill histórico: `fire_events` con `centroid` no quedan con `department IS NULL` salvo casos fuera de cobertura.

---

## Riesgos

| Riesgo | Mitigación |
|--------|------------|
| API Georef caída o lenta | Fallback a GeoJSON; cache local del archivo |
| Nombres de departamentos no coinciden con convenciones existentes | No hay convención previa (no había departamentos). Los nombres vienen del IGN |
| Geometrías con SRID distinto a 4326 | Forzar `ST_SetSRID(..., 4326)` en el INSERT |
| Duplicados por carga repetida | Política de carga full con guard-rail por conteo (`>=500` aborta, `0` habilita); no hacer merge incremental sin `georef_id` estable |
