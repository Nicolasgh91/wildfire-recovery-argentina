-- Assign province and department from a centroid point.
-- Robust to regions SRID mismatches (0 or non-4326) and border cases.

CREATE OR REPLACE FUNCTION public.assign_province_department(
    p_centroid GEOGRAPHY
)
RETURNS TABLE (province VARCHAR, department VARCHAR)
LANGUAGE sql
STABLE
AS $$
    WITH point_input AS (
        SELECT
            ST_Transform(
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
        SELECT province_candidate.name
        FROM (
            SELECT
                r.name,
                1 AS match_priority,
                ST_Distance(r.geom_4326, p.point_geom) AS dist,
                r.id
            FROM regions_normalized r
            CROSS JOIN point_input p
            WHERE r.category = 'PROVINCIA'
              AND ST_Covers(r.geom_4326, p.point_geom)
            UNION ALL
            SELECT
                r.name,
                2 AS match_priority,
                ST_Distance(r.geom_4326, p.point_geom) AS dist,
                r.id
            FROM regions_normalized r
            CROSS JOIN point_input p
            WHERE r.category = 'PROVINCIA'
              AND ST_Intersects(r.geom_4326, p.point_geom)
        ) AS province_candidate
        ORDER BY province_candidate.match_priority, province_candidate.dist, province_candidate.id
        LIMIT 1
    ),
    department_pick AS (
        SELECT department_candidate.name
        FROM (
            SELECT
                r.name,
                1 AS match_priority,
                ST_Distance(r.geom_4326, p.point_geom) AS dist,
                r.id
            FROM regions_normalized r
            CROSS JOIN point_input p
            WHERE r.category = 'DEPARTAMENTO'
              AND ST_Covers(r.geom_4326, p.point_geom)
            UNION ALL
            SELECT
                r.name,
                2 AS match_priority,
                ST_Distance(r.geom_4326, p.point_geom) AS dist,
                r.id
            FROM regions_normalized r
            CROSS JOIN point_input p
            WHERE r.category = 'DEPARTAMENTO'
              AND ST_Intersects(r.geom_4326, p.point_geom)
        ) AS department_candidate
        ORDER BY department_candidate.match_priority, department_candidate.dist, department_candidate.id
        LIMIT 1
    )
    SELECT
        p.name::VARCHAR AS province,
        d.name::VARCHAR AS department
    FROM province_pick p
    LEFT JOIN department_pick d ON TRUE;
$$;
