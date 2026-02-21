-- =============================================================================
-- FORESTGUARD - ACCOUNT DELETE FK ALIGNMENT (PR5 ENFORCEMENT)
-- =============================================================================
-- Objective:
--   Enforce evidence-preserving behavior for citizen reports when deleting users:
--   citizen_reports.reporter_user_id -> users(id) ON DELETE SET NULL
--
-- Rules:
--   1) If FK exists with a different action, replace it.
--   2) If FK does not exist, create it.
--   3) If table/column is missing, fail immediately.
-- =============================================================================

DO $$
DECLARE
    table_exists BOOLEAN;
    column_exists BOOLEAN;
    existing_constraint TEXT;
BEGIN
    SELECT EXISTS (
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_name = 'citizen_reports'
    ) INTO table_exists;

    IF NOT table_exists THEN
        RAISE EXCEPTION 'citizen_reports table is required for account deletion policy enforcement';
    END IF;

    SELECT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'citizen_reports'
          AND column_name = 'reporter_user_id'
    ) INTO column_exists;

    IF NOT column_exists THEN
        RAISE EXCEPTION 'citizen_reports.reporter_user_id column is required for account deletion policy enforcement';
    END IF;

    -- ON DELETE SET NULL requires nullable column.
    EXECUTE 'ALTER TABLE public.citizen_reports ALTER COLUMN reporter_user_id DROP NOT NULL';

    SELECT tc.constraint_name
    INTO existing_constraint
    FROM information_schema.table_constraints tc
    JOIN information_schema.key_column_usage kcu
      ON tc.constraint_name = kcu.constraint_name
     AND tc.table_schema = kcu.table_schema
    WHERE tc.table_schema = 'public'
      AND tc.table_name = 'citizen_reports'
      AND tc.constraint_type = 'FOREIGN KEY'
      AND kcu.column_name = 'reporter_user_id'
    LIMIT 1;

    IF existing_constraint IS NOT NULL THEN
        EXECUTE format(
            'ALTER TABLE public.citizen_reports DROP CONSTRAINT %I',
            existing_constraint
        );
    END IF;

    EXECUTE '
        ALTER TABLE public.citizen_reports
        ADD CONSTRAINT citizen_reports_reporter_user_id_fkey
        FOREIGN KEY (reporter_user_id)
        REFERENCES public.users(id)
        ON DELETE SET NULL
    ';
END $$;

-- Verification query (should return confdeltype = ''n'' for SET NULL)
SELECT
    c.conname,
    c.confdeltype
FROM pg_constraint c
JOIN pg_class t ON t.oid = c.conrelid
JOIN pg_namespace n ON n.oid = t.relnamespace
JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(c.conkey)
WHERE n.nspname = 'public'
  AND t.relname = 'citizen_reports'
  AND c.contype = 'f'
  AND a.attname = 'reporter_user_id';

