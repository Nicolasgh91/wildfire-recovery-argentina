-- Supabase security fixes: extensions, RLS policies, and function search_path

-- 1) Move extensions out of public schema (reduces exposure and fixes linter warnings)
CREATE SCHEMA IF NOT EXISTS extensions;

DO $$
DECLARE
  postgis_relocatable BOOLEAN;
BEGIN
  IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'postgis') THEN
    SELECT extrelocatable INTO postgis_relocatable
    FROM pg_extension
    WHERE extname = 'postgis';

    IF postgis_relocatable THEN
      EXECUTE 'ALTER EXTENSION postgis SET SCHEMA extensions';
    ELSE
      RAISE NOTICE 'PostGIS is not relocatable in this environment. See Supabase docs for the manual relocation steps.';
    END IF;
  END IF;

  IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm') THEN
    EXECUTE 'ALTER EXTENSION pg_trgm SET SCHEMA extensions';
  END IF;
END $$;

GRANT USAGE ON SCHEMA extensions TO public;

-- Ensure Supabase roles can resolve extension functions without schema prefix
DO $$
DECLARE
  r TEXT;
BEGIN
  FOREACH r IN ARRAY ARRAY['postgres','authenticator','anon','authenticated','service_role'] LOOP
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
      EXECUTE format('ALTER ROLE %I SET search_path = public, extensions', r);
    END IF;
  END LOOP;
END $$;

-- 2) Fix function search_path mutability warning
DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'public' AND p.proname = 'update_users_updated_at'
  ) THEN
    EXECUTE 'ALTER FUNCTION public.update_users_updated_at() SET search_path = public';
  END IF;
END $$;

-- 3) Tighten RLS policies (avoid WITH CHECK (true))
-- RLS for spatial_ref_sys (if still in public)
--DO $$
--BEGIN
--IF EXISTS (
--  SELECT 1
--  FROM information_schema.tables
--  WHERE table_schema = 'public' AND table_name = 'spatial_ref_sys'
--) THEN
--  EXECUTE 'ALTER TABLE public.spatial_ref_sys ENABLE ROW LEVEL SECURITY';
--  EXECUTE 'DROP POLICY IF EXISTS \"Public Read\" ON public.spatial_ref_sys';
--  EXECUTE 'CREATE POLICY \"Public Read\" ON public.spatial_ref_sys FOR SELECT TO anon, authenticated, service_role USING (true)';
--END IF;
--END $$;

-- Citizen reports: keep public insert but enforce minimum description length
DROP POLICY IF EXISTS "Public Insert" ON citizen_reports;
CREATE POLICY "Public Insert" ON citizen_reports
  FOR INSERT
  TO anon, authenticated
  WITH CHECK (description IS NOT NULL AND char_length(description) >= 20);

DROP POLICY IF EXISTS users_insert ON users;
