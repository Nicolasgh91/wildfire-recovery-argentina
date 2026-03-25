-- F1-T02 diagnostics for regions geometry and spatial index usage.
-- Read-only checks plus safe index creation if missing.

-- 1) Distribution by category.
SELECT category, COUNT(*) AS total
FROM public.regions
GROUP BY category
ORDER BY category;

-- 2) Geometry metadata (SRID/type trap detection).
SELECT f_geometry_column, srid, type
FROM geometry_columns
WHERE f_table_name = 'regions';

-- 3) Check common "capital" departments are present.
SELECT name, category
FROM public.regions
WHERE category = 'DEPARTAMENTO'
  AND name ILIKE '%capital%'
ORDER BY name
LIMIT 20;

-- 4) Control points coverage checks.
-- Cordoba city center.
SELECT name
FROM public.regions
WHERE category = 'PROVINCIA'
  AND ST_Intersects(geom::geometry, ST_SetSRID(ST_MakePoint(-64.18, -31.42), 4326));

SELECT name
FROM public.regions
WHERE category = 'DEPARTAMENTO'
  AND ST_Intersects(geom::geometry, ST_SetSRID(ST_MakePoint(-64.18, -31.42), 4326));

-- Approximate Cordoba/Santa Fe border point.
SELECT category, name
FROM public.regions
WHERE category IN ('PROVINCIA', 'DEPARTAMENTO')
  AND ST_Intersects(geom::geometry, ST_SetSRID(ST_MakePoint(-62.0, -32.0), 4326))
ORDER BY category, name;

-- Patagonia southern control point.
SELECT category, name
FROM public.regions
WHERE category IN ('PROVINCIA', 'DEPARTAMENTO')
  AND ST_Intersects(geom::geometry, ST_SetSRID(ST_MakePoint(-68.3, -54.8), 4326))
ORDER BY category, name;

-- 5) Ensure GiST index exists.
SELECT indexname, indexdef
FROM pg_indexes
WHERE schemaname = 'public'
  AND tablename = 'regions'
  AND indexdef ILIKE '%USING gist%';

CREATE INDEX IF NOT EXISTS idx_regions_geom_gist
ON public.regions USING GIST (geom);

-- 6) Explain function lookup for planner/index verification.
EXPLAIN (ANALYZE, BUFFERS, VERBOSE)
SELECT *
FROM public.assign_province_department(
    ST_SetSRID(ST_MakePoint(-64.18, -31.42), 4326)::geography
);
