-- WARNING: This schema is for context only and is not meant to be run.
-- Table order and constraints may not be valid for execution.

CREATE TABLE public.audit_events (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  principal_id character varying,
  principal_role character varying,
  action character varying NOT NULL CHECK (length(action::text) > 0),
  resource_type character varying,
  resource_id uuid,
  details jsonb,
  ip_address inet,
  user_agent text,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT audit_events_pkey PRIMARY KEY (id)
);
CREATE TABLE public.burn_certificates (
  fire_event_id uuid NOT NULL,
  issued_to character varying NOT NULL,
  requester_email character varying,
  certificate_number character varying NOT NULL UNIQUE,
  data_hash character varying NOT NULL UNIQUE,
  snapshot_data text NOT NULL,
  verification_url character varying,
  issued_at timestamp with time zone DEFAULT now(),
  valid_until timestamp with time zone,
  status character varying,
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT burn_certificates_pkey PRIMARY KEY (id),
  CONSTRAINT burn_certificates_fire_event_id_fkey FOREIGN KEY (fire_event_id) REFERENCES public.fire_events(id)
);
CREATE TABLE public.citizen_reports (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  reported_location USER-DEFINED NOT NULL,
  reported_latitude double precision NOT NULL,
  reported_longitude double precision NOT NULL,
  location_description text,
  report_type character varying,
  description text NOT NULL,
  observed_date date,
  user_photos ARRAY,
  reporter_name character varying,
  reporter_email character varying,
  reporter_phone character varying,
  is_anonymous boolean DEFAULT false,
  reporter_organization character varying,
  related_fire_events ARRAY,
  related_protected_areas ARRAY,
  historical_fires_in_area integer,
  evidence_package_url text,
  status character varying DEFAULT 'submitted'::character varying,
  reviewed_by character varying,
  reviewed_at timestamp with time zone,
  authority_notified character varying,
  authority_notified_at timestamp with time zone,
  internal_notes text,
  is_public boolean DEFAULT false,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT citizen_reports_pkey PRIMARY KEY (id)
);
CREATE TABLE public.fire_detections (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  satellite character varying NOT NULL,
  instrument character varying NOT NULL,
  detected_at timestamp with time zone NOT NULL,
  location USER-DEFINED NOT NULL,
  latitude numeric NOT NULL,
  longitude numeric NOT NULL,
  bt_mir_kelvin numeric,
  bt_tir_kelvin numeric,
  fire_radiative_power numeric,
  confidence_raw character varying,
  confidence_normalized integer,
  acquisition_date date,
  acquisition_time time without time zone,
  daynight character varying,
  is_processed boolean,
  fire_event_id uuid,
  CONSTRAINT fire_detections_pkey PRIMARY KEY (id),
  CONSTRAINT fire_detections_fire_event_id_fkey FOREIGN KEY (fire_event_id) REFERENCES public.fire_events(id)
);
CREATE TABLE public.fire_events (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  centroid USER-DEFINED NOT NULL,
  perimeter USER-DEFINED,
  start_date timestamp with time zone NOT NULL,
  end_date timestamp with time zone NOT NULL,
  total_detections integer,
  avg_frp numeric,
  max_frp numeric,
  sum_frp numeric,
  avg_confidence numeric,
  estimated_area_hectares numeric,
  province character varying,
  department character varying,
  is_significant boolean,
  processing_error character varying,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  has_legal_analysis boolean DEFAULT false,
  CONSTRAINT fire_events_pkey PRIMARY KEY (id)
);
CREATE TABLE public.fire_protected_area_intersections (
  fire_event_id uuid NOT NULL,
  protected_area_id uuid NOT NULL,
  intersection_geometry USER-DEFINED,
  intersection_area_hectares double precision,
  overlap_percentage double precision,
  fire_date date NOT NULL,
  prohibition_until date NOT NULL,
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT fire_protected_area_intersections_pkey PRIMARY KEY (id),
  CONSTRAINT fire_protected_area_intersections_fire_event_id_fkey FOREIGN KEY (fire_event_id) REFERENCES public.fire_events(id),
  CONSTRAINT fire_protected_area_intersections_protected_area_id_fkey FOREIGN KEY (protected_area_id) REFERENCES public.protected_areas(id)
);
CREATE TABLE public.forensic_cases (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  fire_event_id uuid NOT NULL,
  protected_area_id uuid NOT NULL,
  burned_area_hectares numeric NOT NULL,
  overlap_percentage numeric NOT NULL,
  status character varying DEFAULT 'open'::character varying CHECK (status::text = ANY (ARRAY['open'::character varying, 'analyzing'::character varying, 'confirmed_violation'::character varying, 'dismissed'::character varying]::text[])),
  priority character varying DEFAULT 'medium'::character varying CHECK (priority::text = ANY (ARRAY['low'::character varying, 'medium'::character varying, 'high'::character varying, 'critical'::character varying]::text[])),
  final_verdict text,
  assigned_auditor character varying,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT forensic_cases_pkey PRIMARY KEY (id),
  CONSTRAINT fk_forensic_fire FOREIGN KEY (fire_event_id) REFERENCES public.fire_events(id),
  CONSTRAINT fk_forensic_pa FOREIGN KEY (protected_area_id) REFERENCES public.protected_areas(id)
);
CREATE TABLE public.idempotency_keys (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  idempotency_key character varying NOT NULL,
  endpoint character varying NOT NULL,
  request_hash character varying NOT NULL,
  response_status_code integer,
  response_body jsonb,
  created_at timestamp with time zone DEFAULT now(),
  expires_at timestamp with time zone DEFAULT (now() + '24:00:00'::interval),
  CONSTRAINT idempotency_keys_pkey PRIMARY KEY (id)
);
CREATE TABLE public.land_use_audits (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  queried_latitude double precision NOT NULL,
  queried_longitude double precision NOT NULL,
  queried_location USER-DEFINED,
  search_radius_meters integer,
  fires_found integer DEFAULT 0,
  is_violation boolean DEFAULT false,
  violation_severity character varying,
  prohibition_until date,
  earliest_fire_date date,
  latest_fire_date date,
  user_ip inet,
  user_agent text,
  query_duration_ms integer,
  queried_at timestamp with time zone DEFAULT now(),
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT land_use_audits_pkey PRIMARY KEY (id)
);
CREATE TABLE public.land_use_changes (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  fire_event_id uuid NOT NULL,
  monitoring_record_id uuid,
  change_detected_at date NOT NULL,
  months_after_fire integer,
  change_type character varying NOT NULL,
  change_severity character varying,
  before_image_id uuid,
  after_image_id uuid,
  change_detection_image_url text,
  affected_area_hectares double precision,
  is_potential_violation boolean DEFAULT false,
  violation_confidence character varying,
  status character varying DEFAULT 'pending_review'::character varying,
  reviewed_by character varying,
  reviewed_at timestamp with time zone,
  notes text,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT land_use_changes_pkey PRIMARY KEY (id),
  CONSTRAINT land_use_changes_fire_event_id_fkey FOREIGN KEY (fire_event_id) REFERENCES public.fire_events(id)
);
CREATE TABLE public.protected_areas (
  official_name character varying NOT NULL,
  alternative_names ARRAY,
  category character varying NOT NULL CHECK (category::text = ANY (ARRAY['national_park'::character varying, 'national_reserve'::character varying, 'natural_monument'::character varying, 'provincial_reserve'::character varying, 'provincial_park'::character varying, 'biosphere_reserve'::character varying, 'ramsar_site'::character varying, 'world_heritage'::character varying, 'municipal_reserve'::character varying, 'private_reserve'::character varying, 'wildlife_refuge'::character varying, 'marine_park'::character varying, 'other'::character varying]::text[])),
  boundary USER-DEFINED NOT NULL,
  simplified_boundary USER-DEFINED,
  centroid USER-DEFINED,
  area_hectares double precision,
  jurisdiction character varying CHECK (jurisdiction IS NULL OR (jurisdiction::text = ANY (ARRAY['national'::character varying, 'provincial'::character varying, 'municipal'::character varying, 'private'::character varying]::text[]))),
  province character varying,
  department character varying,
  prohibition_years integer NOT NULL CHECK (prohibition_years = ANY (ARRAY[30, 60])),
  established_date date,
  managing_authority character varying,
  wdpa_id integer UNIQUE,
  iucn_category character varying,
  source_dataset character varying,
  source_url text,
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT protected_areas_pkey PRIMARY KEY (id)
);
CREATE TABLE public.recovery_metrics (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  forensic_case_id uuid NOT NULL,
  year_analyzed integer NOT NULL,
  avg_ndvi numeric,
  avg_nbr numeric,
  detected_class USER-DEFINED,
  thumbnail_url text,
  satellite_image_url text,
  analyzed_at timestamp with time zone DEFAULT now(),
  CONSTRAINT recovery_metrics_pkey PRIMARY KEY (id),
  CONSTRAINT fk_metrics_case FOREIGN KEY (forensic_case_id) REFERENCES public.forensic_cases(id)
);
CREATE TABLE public.regions (
  id integer NOT NULL DEFAULT nextval('regions_id_seq'::regclass),
  name character varying NOT NULL,
  category character varying NOT NULL CHECK (category::text = ANY (ARRAY['PROVINCIA'::character varying, 'DEPARTAMENTO'::character varying, 'MUNICIPIO'::character varying]::text[])),
  geom USER-DEFINED NOT NULL,
  CONSTRAINT regions_pkey PRIMARY KEY (id)
);
CREATE TABLE public.spatial_ref_sys (
  srid integer NOT NULL CHECK (srid > 0 AND srid <= 998999),
  auth_name character varying,
  auth_srid integer,
  srtext character varying,
  proj4text character varying,
  CONSTRAINT spatial_ref_sys_pkey PRIMARY KEY (srid)
);

-- ==============================================
-- OPTIMIZATIONS & SECURITY (RFC 003)
-- ==============================================

-- Migration: Add indexes for FireEvent optimization (UC-13)
-- Description: Improves performance of filtering and ordering by start_date, province, and significance.

-- Index for default ordering (Recent fires first)
CREATE INDEX IF NOT EXISTS idx_fire_events_start_date_desc ON fire_events (start_date DESC);

-- Indexes for common filters
CREATE INDEX IF NOT EXISTS idx_fire_events_province ON fire_events (province);
CREATE INDEX IF NOT EXISTS idx_fire_events_is_significant ON fire_events (is_significant);

-- Composite index for most frequent query pattern (Significant + Date)
CREATE INDEX IF NOT EXISTS idx_fire_events_significant_date ON fire_events (is_significant, start_date DESC);

-- Migration: Create Audit Events table and standardize RLS policies
-- Purpose: Support Multi-tenancy, Auditing, and Role-Based Security

-- 1. Create Audit Events Table (Append-Only Log)
CREATE TABLE IF NOT EXISTS audit_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    principal_id VARCHAR(255),          -- Who (User ID / API Key / Email)
    principal_role VARCHAR(50),         -- Role at time of action (admin, user, public)
    action VARCHAR(100) NOT NULL,       -- What (create, update, delete, login, etc.)
    resource_type VARCHAR(100),         -- Where (table/entity name)
    resource_id UUID,                   -- Specific entity ID
    details JSONB,                      -- Changes or metadata
    ip_address INET,                    -- From Where (IP)
    user_agent TEXT,                    -- From Where (Client)
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraint to enforce append-only (Trigger needed ideally, or just convention)
    CONSTRAINT audit_events_action_check CHECK (length(action) > 0)
);

CREATE INDEX IF NOT EXISTS idx_audit_events_created_at ON audit_events (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_events_principal_id ON audit_events (principal_id);
CREATE INDEX IF NOT EXISTS idx_audit_events_resource ON audit_events (resource_type, resource_id);

-- 2. Enable RLS on core tables
ALTER TABLE audit_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE fire_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE citizen_reports ENABLE ROW LEVEL SECURITY;

-- 3. Define RLS Policies (Standardized Patterns)

-- Usage Context: 
-- These policies are enforced when accessing via Supabase Client (Anon/Authenticated).
-- FastAPI Backend typically uses 'service_role' which BYPASSES RLS.

-- PATTERN A: Public Read, Admin Write (Reference Data)
-- Table: fire_events
CREATE POLICY "Public Read Access" ON fire_events
    FOR SELECT
    TO anon, authenticated, service_role
    USING (true);

CREATE POLICY "Admin Write Access" ON fire_events
    FOR ALL
    TO service_role
    USING (true);

-- PATTERN B: Sensitive System Data (Admin Only)
-- Table: audit_events
CREATE POLICY "Admin Read Access" ON audit_events
    FOR SELECT
    TO service_role
    USING (true);
    
-- No public write access to audit log (handled by backend functions)

-- PATTERN C: User Data (Insert Public, View/Edit Admin/Owner)
-- Table: citizen_reports
CREATE POLICY "Public Insert" ON citizen_reports
    FOR INSERT
    TO anon, authenticated
    WITH CHECK (true);

CREATE POLICY "Admin Full Access" ON citizen_reports
    FOR ALL
    TO service_role
    USING (true);

-- Note: In a true SaaS with Supabase Auth, we would add:
-- CREATE POLICY "User View Own" ON citizen_reports 
-- FOR SELECT USING (auth.uid() = user_id);