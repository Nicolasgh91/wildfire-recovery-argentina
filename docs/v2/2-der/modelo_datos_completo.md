# ForestGuard - Modelo de Datos (DER) v2.0

**Fecha de actualización**: Febrero 2026  
**Versión del esquema**: 2.0 (incluye 23 migraciones)  
**Base de datos**: PostgreSQL 15.x + PostGIS 3.3 + H3  
**Hosting**: Supabase (500MB free tier)

---

## 1. Visión General del Modelo de Datos

El modelo de datos de ForestGuard está diseñado para:

1. **Rastrear incendios forestales** desde detecciones satelitales individuales hasta eventos agregados
2. **Agrupar macroscópicamente** eventos en episodios para optimizar requests a GEE
3. **Garantizar trazabilidad legal** con auditorías inmutables y hashes SHA-256
4. **Soportar análisis espacial** con índices H3 y PostGIS
5. **Reproducir evidencia satelital** almacenando metadata GEE en lugar de imágenes HD
6. **Gestionar pagos y créditos** para servicios premium (reportes forenses, imágenes HD)

### Estadísticas del Schema

- **30+ tablas principales**
- **3 materialized views** (h3_recurrence_stats, fire_stats, fire_event_quality_metrics)
- **23 migraciones SQL** desde el schema base
- **RLS habilitado** en todas las tablas sensibles
- **Particionado** en fire_detections por fecha

---

## 2. Diagrama Entidad-Relación Consolidado

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         FORESTGUARD DATA MODEL v2.0                              │
└─────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                           CORE FIRE DETECTION & EVENTS                        │
└──────────────────────────────────────────────────────────────────────────────┘

    ┌─────────────────────────┐
    │   fire_detections        │◄─────────┐
    ├─────────────────────────┤          │  NASA FIRMS
    │ id (PK)                 │          │  CSV Ingestion
    │ satellite               │          │
    │ instrument              │          │
    │ detected_at             │          │
    │ location (POINT)        │          │
    │ latitude, longitude     │          │
    │ bt_mir_kelvin           │          │
    │ bt_tir_kelvin           │          │
    │ fire_radiative_power    │          │
    │ confidence_normalized   │          │
    │ h3_index (BIGINT)       │───┐      │
    │ fire_event_id (FK)      │───┼───┐  │
    │ is_processed            │   │   │  │
    └─────────────────────────┘   │   │  │
              │                   │   │  │
              │ ST-DBSCAN         │   │  │
              │ Clustering        │   │  │
              ▼                   │   │  │
    ┌─────────────────────────┐   │   │  │
    │   fire_events           │◄──┼───┘  │
    ├─────────────────────────┤   │      │
    │ id (PK)                 │   │      │
    │ centroid (POINT)        │   │      │
    │ perimeter (POLYGON)     │   │      │
    │ start_date, end_date    │   │      │
    │ total_detections        │   │      │
    │ avg_frp, max_frp        │   │      │
    │ estimated_area_hectares │   │      │
    │ province, department    │   │      │
    │ status (enum)           │   │      │
    │ h3_index (BIGINT)       │◄──┘      │
    │ slides_data (JSONB)     │          │  GEE carousel metadata
    │ last_gee_image_id       │◄─────────┘  Reproducibility key
    │ has_historic_report     │
    │ has_legal_analysis      │
    │ clustering_version_id   │───┐
    └─────────────────────────┘   │
              │                   │
              │                   │
              ▼                   │
    ┌─────────────────────────┐   │
    │  fire_episodes          │   │  Macro grouping (UC-F13)
    ├─────────────────────────┤   │
    │ id (PK)                 │   │
    │ status (enum)           │   │
    │ start_date, end_date    │   │
    │ centroid_lat/lon        │   │
    │ bbox (minx/miny/maxx/y) │   │
    │ provinces (ARRAY)       │   │
    │ event_count             │   │
    │ frp_sum, frp_max        │   │
    │ estimated_area_hectares │   │
    │ gee_candidate (bool)    │   │  Eligibility for GEE batch
    │ gee_priority (int)      │   │  Scoring for request order
    │ slides_data (JSONB)     │   │  Episode-level carousel
    │ requires_recalculation  │   │  Flag for re-clustering
    │ clustering_version_id   │◄──┘
    │ dnbr_severity           │      Post-fire severity index
    │ severity_class          │
    └─────────────────────────┘
              │
              │ N:M
              ▼
    ┌─────────────────────────┐
    │ fire_episode_events     │   Junction table
    ├─────────────────────────┤
    │ episode_id (PK, FK)     │
    │ event_id (PK, FK)       │
    │ added_at                │
    └─────────────────────────┘

    ┌─────────────────────────┐
    │ clustering_versions     │   Algorithm version tracking
    ├─────────────────────────┤
    │ id (PK)                 │
    │ version_name            │
    │ epsilon_km              │   ST-DBSCAN spatial threshold
    │ min_points              │   ST-DBSCAN density threshold
    │ temporal_window_hours   │   Time window for clustering
    │ algorithm (enum)        │
    │ is_active               │
    │ created_by (FK users)   │
    └─────────────────────────┘

    ┌─────────────────────────┐
    │ episode_mergers         │   Episode merge history
    ├─────────────────────────┤
    │ id (PK)                 │
    │ absorbed_episode_id (FK)│
    │ absorbing_episode_id(FK)│
    │ merged_at               │
    │ reason (enum)           │
    │ merged_by_version_id(FK)│
    │ notes                   │
    └─────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                      PROTECTED AREAS & LEGAL COMPLIANCE                       │
└──────────────────────────────────────────────────────────────────────────────┘

    ┌─────────────────────────┐
    │  protected_areas        │
    ├─────────────────────────┤
    │ id (PK)                 │
    │ official_name           │
    │ category (enum)         │   national_park, reserve, etc.
    │ boundary (MULTIPOLYGON) │
    │ simplified_boundary     │   For faster rendering
    │ centroid (POINT)        │
    │ area_hectares           │
    │ jurisdiction (enum)     │   national/provincial/municipal
    │ province, department    │
    │ prohibition_years (int) │   30 o 60 según Ley 26.815
    │ wdpa_id (int UNIQUE)    │   World Database on Protected Areas
    │ iucn_category           │
    │ carrying_capacity (int) │   For UC-04 alerts
    └─────────────────────────┘
              │
              │ Spatial Join with fire_events
              ▼
    ┌──────────────────────────────────────┐
    │ fire_protected_area_intersections    │   Legal evidence (UC-F06)
    ├──────────────────────────────────────┤
    │ id (PK)                              │
    │ fire_event_id (FK)                   │
    │ protected_area_id (FK)               │
    │ intersection_geometry (POLYGON)      │
    │ intersection_area_hectares           │
    │ overlap_percentage                   │
    │ fire_date                            │
    │ prohibition_until                    │   Calculated: fire_date + 30/60 years
    └──────────────────────────────────────┘

    ┌─────────────────────────┐
    │  land_use_audits        │   UC-F06 audit log (immutable)
    ├─────────────────────────┤
    │ id (PK)                 │
    │ queried_latitude        │
    │ queried_longitude       │
    │ queried_location (POINT)│
    │ search_radius_meters    │
    │ fires_found (int)       │
    │ is_violation (bool)     │
    │ violation_severity      │
    │ prohibition_until       │
    │ earliest_fire_date      │
    │ latest_fire_date        │
    │ user_ip (inet)          │
    │ user_agent              │
    │ query_duration_ms       │
    │ queried_at              │
    └─────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                       SATELLITE IMAGERY & REPRODUCIBILITY                     │
└──────────────────────────────────────────────────────────────────────────────┘

    ┌─────────────────────────┐
    │  satellite_images       │   UC-F08/F09/F13 imagery metadata
    ├─────────────────────────┤
    │ id (PK)                 │
    │ fire_event_id (FK)      │
    │ satellite               │   e.g., "Sentinel-2"
    │ tile_id                 │
    │ product_id              │
    │ acquisition_date        │
    │ acquisition_time        │
    │ days_after_fire (int)   │
    │ image_type (enum)       │   "before", "during", "after"
    │ cloud_cover_pct         │
    │ quality_score           │
    │ usable_for_analysis     │
    │ r2_bucket               │   Cloudflare R2 storage
    │ r2_key                  │   Object key
    │ r2_url                  │   Public URL (thumbnails)
    │ thumbnail_url           │   Low-res preview
    │ file_size_mb            │
    │ bands_included (ARRAY)  │
    │ processing_level        │
    │ spatial_resolution_m    │
    │ gee_system_index        │   🔑 KEY: GEE reproducibility
    │ visualization_params    │   🔑 KEY: Bands config (JSONB)
    │ is_reproducible (bool)  │
    └─────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                          CLIMATE & ENVIRONMENTAL DATA                         │
└──────────────────────────────────────────────────────────────────────────────┘

    ┌─────────────────────────┐
    │  climate_data           │   Open-Meteo integration
    ├─────────────────────────┤
    │ id (PK)                 │
    │ location (POINT)        │
    │ latitude, longitude     │
    │ recorded_at             │
    │ data_source             │   e.g., "open-meteo"
    │ temperature_2m          │
    │ relative_humidity_2m    │
    │ wind_speed_10m          │
    │ wind_direction_10m      │
    │ wind_gusts_10m          │
    │ precipitation           │
    │ soil_moisture_0_to_10cm │
    │ evapotranspiration      │
    │ vapor_pressure_deficit  │
    │ fire_weather_index      │
    │ drought_code            │
    └─────────────────────────┘
              │
              │ Spatial + temporal join
              ▼
    ┌───────────────────────────────┐
    │ fire_climate_associations     │   UC-F04 quality metrics
    ├───────────────────────────────┤
    │ id (PK)                       │
    │ fire_event_id (FK)            │
    │ climate_data_id (FK)          │
    │ association_type (enum)       │   "before", "during", "after", "peak"
    │ hours_offset (int)            │
    │ distance_km                   │
    │ relevance_weight (0.0-1.0)    │
    └───────────────────────────────┘

    ┌─────────────────────────┐
    │ data_source_metadata    │   UC-F04 transparency
    ├─────────────────────────┤
    │ id (PK)                 │
    │ source_name UNIQUE      │   e.g., "NASA_FIRMS_VIIRS"
    │ source_type (enum)      │   satellite_detection/imagery/climate
    │ provider                │
    │ provider_url            │
    │ api_endpoint            │
    │ spatial_resolution_m    │
    │ temporal_resolution_h   │
    │ update_frequency        │
    │ coverage_description    │
    │ coverage_start_date     │
    │ accuracy_description    │
    │ known_limitations(ARRAY)│
    │ confidence_baseline     │
    │ quality_weight (0-1)    │
    │ is_active               │
    │ last_validated_at       │
    └─────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                       VEGETATION MONITORING & LAND USE                        │
└──────────────────────────────────────────────────────────────────────────────┘

    ┌─────────────────────────┐
    │ vegetation_monitoring   │   UC-F12 (VAE) - Recovery tracking
    ├─────────────────────────┤
    │ id (PK)                 │
    │ fire_event_id (FK)      │
    │ satellite_image_id (FK) │
    │ month_number            │
    │ monitoring_date         │
    │ months_after_fire       │
    │ ndvi_mean               │   Vegetation index
    │ ndvi_min, ndvi_max      │
    │ ndvi_std_dev            │
    │ baseline_ndvi           │   Pre-fire baseline
    │ recovery_percentage     │
    │ land_use_classification │
    │ classification_confidence│
    │ human_activity_detected │
    │ activity_type           │
    │ activity_confidence     │
    │ notes                   │
    │ analyst_name            │
    └─────────────────────────┘

    ┌─────────────────────────┐
    │ land_use_changes        │   UC-F12 change detection
    ├─────────────────────────┤
    │ id (PK)                 │
    │ fire_event_id (FK)      │
    │ monitoring_record_id(FK)│
    │ change_detected_at      │
    │ months_after_fire       │
    │ change_type (enum)      │   agriculture, urban_development, etc.
    │ change_severity         │
    │ before_image_id (FK)    │
    │ after_image_id (FK)     │
    │ change_detection_img_url│
    │ affected_area_hectares  │
    │ is_potential_violation  │
    │ violation_confidence    │
    │ status (enum)           │
    │ reviewed_by             │
    │ reviewed_at             │
    │ notes                   │
    └─────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                   USER MANAGEMENT & AUTHENTICATION                            │
└──────────────────────────────────────────────────────────────────────────────┘

    ┌─────────────────────────┐
    │  users                  │   Supabase Auth integration
    ├─────────────────────────┤
    │ id (PK)                 │   UUID from auth.users
    │ email UNIQUE            │
    │ password_hash           │   Hashed by Supabase
    │ dni UNIQUE              │   Argentina national ID
    │ full_name               │
    │ role (enum)             │   'admin' | 'user'
    │ google_id UNIQUE        │   OAuth integration
    │ avatar_url              │
    │ created_at              │
    │ last_login_at           │
    │ is_verified             │
    └─────────────────────────┘
              │
              │ 1:N
              ▼
    ┌─────────────────────────┐
    │ user_saved_filters      │   T1.7 - UC-F03 dashboard preferences
    ├─────────────────────────┤
    │ id (PK)                 │
    │ user_id (FK)            │
    │ filter_name             │
    │ filter_config (JSONB)   │   Stores filter state
    │ is_default              │
    │ created_at              │
    │ last_used_at            │
    │ use_count               │
    └─────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                     PAYMENT SYSTEM & CREDITS (UC-F10/F11)                     │
└──────────────────────────────────────────────────────────────────────────────┘

    ┌─────────────────────────┐
    │ payment_requests        │   MercadoPago integration
    ├─────────────────────────┤
    │ id (PK)                 │
    │ user_id (FK)            │
    │ status (enum)           │   pending/approved/rejected/expired/refunded
    │ provider (enum)         │   mercadopago/manual/promotional
    │ purpose (enum)          │   report/credits
    │ target_entity_type      │
    │ target_entity_id        │
    │ amount_usd              │
    │ amount_ars              │
    │ external_reference UNIQ │   Our internal ID
    │ provider_payment_id     │   MercadoPago payment ID
    │ provider_preference_id  │   MercadoPago preference ID
    │ checkout_url            │
    │ created_at              │
    │ updated_at              │
    │ expires_at              │
    │ approved_at             │
    │ webhook_received_at     │
    │ retry_count             │
    │ metadata (JSONB)        │
    └─────────────────────────┘
              │
              │ 1:N
              ▼
    ┌─────────────────────────┐
    │ payment_webhook_logs    │   Audit trail (admin-only)
    ├─────────────────────────┤
    │ id (PK)                 │
    │ payment_request_id (FK) │
    │ received_at             │
    │ topic                   │
    │ action                  │
    │ mp_payment_id           │
    │ raw_payload (JSONB)     │   Full webhook body
    │ processing_result       │   success/ignored/error/duplicate
    │ error_message           │
    │ processing_time_ms      │
    └─────────────────────────┘

    ┌─────────────────────────┐
    │ user_credits            │   Credit balance per user
    ├─────────────────────────┤
    │ id (PK)                 │
    │ user_id (FK) UNIQUE     │
    │ balance (int) CHECK≥0   │
    │ created_at              │
    │ updated_at              │
    └─────────────────────────┘
              │
              │ 1:N
              ▼
    ┌─────────────────────────┐
    │ credit_transactions     │   Transaction ledger
    ├─────────────────────────┤
    │ id (PK)                 │
    │ user_id (FK)            │
    │ amount (int)            │   +purchase, -spend
    │ type (enum)             │   purchase/grant/spend/refund/etc.
    │ payment_request_id (FK) │
    │ related_entity_type     │   e.g., "historical_report"
    │ related_entity_id       │
    │ description             │
    │ metadata (JSONB)        │
    │ created_at              │
    └─────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                   SPECIALIZED REPORTS & INVESTIGATIONS                        │
└──────────────────────────────────────────────────────────────────────────────┘

    ┌─────────────────────────┐
    │ exploration_investigations│  UC-F11 wizard investigations
    ├─────────────────────────┤
    │ id (PK)                 │
    │ user_id (FK)            │
    │ fire_event_id (FK)      │
    │ investigation_type      │   historical/judicial
    │ status (enum)           │   draft/submitted/processing/completed/failed
    │ config (JSONB)          │   User selections (images, filters, etc.)
    │ result_pdf_url          │
    │ result_hash             │   SHA-256 verification
    │ total_cost_usd          │
    │ credits_used            │
    │ payment_request_id (FK) │
    │ created_at              │
    │ submitted_at            │
    │ completed_at            │
    │ error_message           │
    └─────────────────────────┘

    ┌─────────────────────────┐
    │ burn_certificates       │   UC-F10 legal certificates
    ├─────────────────────────┤
    │ id (PK)                 │
    │ fire_event_id (FK)      │
    │ issued_to               │
    │ requester_email         │
    │ certificate_number UNIQ │
    │ data_hash UNIQUE        │   SHA-256 of snapshot
    │ snapshot_data (TEXT)    │   Frozen JSON of fire_event state
    │ verification_url        │
    │ issued_at               │
    │ valid_until             │
    │ status (enum)           │
    └─────────────────────────┘

    ┌─────────────────────────┐
    │ forensic_cases          │   UC-F02/F11 judicial cases
    ├─────────────────────────┤
    │ id (PK)                 │
    │ fire_event_id (FK)      │
    │ protected_area_id (FK)  │
    │ burned_area_hectares    │
    │ overlap_percentage      │
    │ status (enum)           │   open/analyzing/confirmed/dismissed
    │ priority (enum)         │   low/medium/high/critical
    │ final_verdict           │
    │ assigned_auditor        │
    │ created_at              │
    │ updated_at              │
    └─────────────────────────┘
              │
              │ 1:N
              ▼
    ┌─────────────────────────┐
    │ recovery_metrics        │   Historical recovery data
    ├─────────────────────────┤
    │ id (PK)                 │
    │ forensic_case_id (FK)   │
    │ year_analyzed           │
    │ avg_ndvi                │
    │ avg_nbr                 │
    │ detected_class (enum)   │
    │ thumbnail_url           │
    │ satellite_image_url     │
    │ analyzed_at             │
    └─────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                     CITIZEN ENGAGEMENT & REPORTING                            │
└──────────────────────────────────────────────────────────────────────────────┘

    ┌─────────────────────────┐
    │ citizen_reports         │   UC-09 public reporting
    ├─────────────────────────┤
    │ id (PK)                 │
    │ reported_location(POINT)│
    │ reported_latitude       │
    │ reported_longitude      │
    │ location_description    │
    │ report_type (enum)      │
    │ description             │
    │ observed_date           │
    │ user_photos (ARRAY)     │
    │ reporter_name           │
    │ reporter_email          │
    │ reporter_phone          │
    │ is_anonymous            │
    │ reporter_organization   │
    │ related_fire_events(ARR)│
    │ related_protected_areas │
    │ historical_fires_in_area│
    │ evidence_package_url    │
    │ status (enum)           │   submitted/under_review/resolved
    │ reviewed_by             │
    │ reviewed_at             │
    │ authority_notified      │
    │ authority_notified_at   │
    │ internal_notes          │
    │ is_public               │
    │ reporter_user_id (FK)   │
    └─────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                       SYSTEM ADMINISTRATION & AUDIT                           │
└──────────────────────────────────────────────────────────────────────────────┘

    ┌─────────────────────────┐
    │ system_parameters       │   Configuration storage
    ├─────────────────────────┤
    │ id (PK)                 │
    │ param_key UNIQUE        │   e.g., "audit_search_radius_max"
    │ param_value (JSONB)     │
    │ description             │
    │ category (enum)         │   general/audit/imagery/reports/etc.
    │ updated_at              │
    │ updated_by (FK users)   │
    │ previous_values (JSONB) │   Version history
    └─────────────────────────┘

    ┌─────────────────────────┐
    │ audit_events            │   Immutable audit log
    ├─────────────────────────┤
    │ id (PK)                 │
    │ principal_id            │   User ID or system identifier
    │ principal_role          │
    │ action                  │
    │ resource_type           │
    │ resource_id             │
    │ details (JSONB)         │
    │ ip_address (inet)       │
    │ user_agent              │
    │ created_at              │
    └─────────────────────────┘

    ┌─────────────────────────┐
    │ idempotency_keys        │   Request deduplication
    ├─────────────────────────┤
    │ id (PK)                 │
    │ idempotency_key UNIQUE  │
    │ endpoint                │
    │ request_hash            │
    │ response_status_code    │
    │ response_body (JSONB)   │
    │ created_at              │
    │ expires_at              │   24 hours
    └─────────────────────────┘

    ┌─────────────────────────┐
    │ fire_stats_refresh_state│   Materialized view refresh control
    ├─────────────────────────┤
    │ id (PK)                 │
    │ fail_count              │
    │ last_error              │
    │ last_run_at             │
    │ next_run_at             │
    └─────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                          SPATIAL & ADMINISTRATIVE                             │
└──────────────────────────────────────────────────────────────────────────────┘

    ┌─────────────────────────┐
    │ regions                 │   Administrative boundaries
    ├─────────────────────────┤
    │ id (PK)                 │
    │ name                    │
    │ category (enum)         │   PROVINCIA/DEPARTAMENTO/MUNICIPIO
    │ geom (MULTIPOLYGON)     │
    └─────────────────────────┘

    ┌─────────────────────────┐
    │ spatial_ref_sys         │   PostGIS SRID definitions
    ├─────────────────────────┤
    │ srid (PK)               │
    │ auth_name               │
    │ auth_srid               │
    │ srtext                  │
    │ proj4text               │
    └─────────────────────────┘
```

---

## 3. Tablas Principales por Categoría

### 3.1 Core Fire Detection (7 tablas)

#### fire_detections
**Propósito**: Detecciones satelitales individuales de NASA FIRMS  
**Volumen**: ~100k+ registros (particionado por fecha)  
**Indices**: `(h3_index)`, `(fire_event_id)`, `(detected_at)`, spatial `(location)`  
**Particionado**: Por `acquisition_date` (mensual)  
**Retención**: 90 días en DB, archivado a Parquet en GCS

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `h3_index` | BIGINT | Índice H3 resolución 8 para análisis espacial |
| `fire_radiative_power` | NUMERIC | FRP en MW, indicador de intensidad |
| `confidence_normalized` | INT | 0-100, normalizado desde raw confidence |

#### fire_events
**Propósito**: Eventos de incendio agregados desde detecciones  
**Volumen**: ~10k+ registros  
**Clustering**: ST-DBSCAN (epsilon_km, min_points, temporal_window_hours)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `slides_data` | JSONB | Array de objetos `{image_type, url, gee_system_index, bands_config}` |
| `last_gee_image_id` | VARCHAR | Último GEE system:index procesado (evita duplicados) |
| `h3_index` | BIGINT | H3 del centroid para recurrence heatmaps |
| `clustering_version_id` | UUID | FK a clustering_versions (trazabilidad de algoritmo) |

**Ejemplo `slides_data`**:
```json
[
  {
    "image_type": "SWIR",
    "url": "https://storage.googleapis.com/.../swir_thumb.png",
    "gee_system_index": "20240215T141059_20240215T141054_T21JUM",
    "bands_config": {"bands": ["B12", "B8A", "B4"], "min": 0, "max": 4000}
  }
]
```

#### fire_episodes
**Propósito**: Macro-agrupación de eventos para optimización GEE  
**Volumen**: ~2k+ registros  
**Relación con events**: N:M vía `fire_episode_events`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `gee_candidate` | BOOL | Elegible para batch GEE request |
| `gee_priority` | INT | Score para ordenar requests GEE (area + FRP + PA overlap) |
| `requires_recalculation` | BOOL | Flag cuando cambian parámetros de clustering |
| `dnbr_severity` | NUMERIC | Diferenced Normalized Burn Ratio (post-cierre) |

---

### 3.2 Legal & Compliance (4 tablas)

#### protected_areas
**Propósito**: Áreas protegidas (parques nacionales, reservas, etc.)  
**Volumen**: ~1000 registros (argentina)  
**Fuente**: WDPA (World Database on Protected Areas) + provincial datasets

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `prohibition_years` | INT | 30 (agricultura) o 60 (bosques) según Ley 26.815 |
| `simplified_boundary` | MULTIPOLYGON | Versión reducida para rendering rápido |
| `carrying_capacity` | INT | UC-04 park capacity alerts |

#### fire_protected_area_intersections
**Propósito**: Evidencia de solapamiento fuego-área protegida  
**Volumen**: ~5k+ registros  
**Cálculo**: `prohibition_until = fire_date + prohibition_years`

**Campos clave**:
- `overlap_percentage`: % del incendio dentro del área protegida
- `intersection_area_hectares`: Superficie afectada dentro del PA

#### land_use_audits
**Propósito**: Registro inmutable de consultas de auditoría legal (UC-F06)  
**Volumen**: ~50k+ registros  
**RLS**: Solo admin puede ver todas, usuario ve las propias

---

### 3.3 Satellite Imagery (1 tabla + metadata en fire_events/episodes)

#### satellite_images
**Propósito**: Metadata de imágenes satelitales con reproducibilidad GEE  
**Volumen**: ~20k+ registros  
**Storage**: Thumbnails en GCS (persistente), HD on-demand (no persiste)

| Campo Crítico | Tipo | Descripción |
|---------------|------|-------------|
| `gee_system_index` | VARCHAR | 🔑 **CLAVE**: Identificador único de imagen GEE |
| `visualization_params` | JSONB | 🔑 **CLAVE**: Config de bandas para reproducir imagen |
| `is_reproducible` | BOOL | TRUE si tiene suficiente metadata para recrear HD |

**Flujo de reproducibilidad**:
1. Usuario solicita reporte con imágenes HD
2. Backend lee `gee_system_index` + `visualization_params` de metadata
3. Celery worker consulta GEE con exact `system:index`
4. GEE retorna imagen HD idéntica
5. Se cobra $0.50 USD, imagen se adjunta a PDF, **no se persiste**

---

### 3.4 Climate & Quality (3 tablas)

#### climate_data
**Propósito**: Datos meteorológicos de Open-Meteo  
**Volumen**: ~200k+ registros  
**Indices**: Spatial `(location)`, temporal `(recorded_at)`

**Campos clave**:
- `fire_weather_index`: FWI (Fire Weather Index)
- `drought_code`: DC del Canadian Forest Fire Danger Rating System

#### data_source_metadata
**Propósito**: Transparencia de fuentes (UC-F04)  
**Volumen**: ~10-20 registros (proveedores)

| Campo | Ejemplo |
|-------|---------|
| `source_name` | "NASA_FIRMS_VIIRS_NRT" |
| `confidence_baseline` | 0.85 |
| `quality_weight` | 0.40 (detections), 0.20 (imagery), 0.20 (climate) |
| `known_limitations` | `["500m spatial resolution", "cloud interference"]` |

#### fire_climate_associations
**Propósito**: Vincular eventos con clima para quality scoring  
**Volumen**: ~100k+ registros  
**Cálculo**: Spatial join (ST_DWithin) + temporal window

---

### 3.5 Payment System (4 tablas)

#### payment_requests
**Propósito**: Solicitudes de pago vía MercadoPago  
**Volumen**: ~5k+ registros esperados  
**Webhook flow**: MercadoPago → `/api/v1/webhooks/mercadopago` → update status

**Estados**:
- `pending`: Checkout creado, esperando pago
- `approved`: Pago confirmado, créditos acreditados
- `rejected`: Pago rechazado
- `expired`: Checkout venció (24h)
- `refunded`: Pago devuelto

#### user_credits
**Propósito**: Saldo de créditos por usuario  
**Volumen**: ~2k+ registros (1 por usuario que compró)  
**CHECK constraint**: `balance >= 0` (previene saldo negativo)

**Función helper**:
```sql
SELECT * FROM get_or_create_user_credits('user-uuid');
```

#### credit_transactions
**Propósito**: Ledger de transacciones (inmutable)  
**Volumen**: ~50k+ registros  
**Tipos**:
- `purchase`: Compra de créditos (+)
- `spend`: Gasto en reporte (-)
- `grant`: Regalo administrativo (+)
- `refund`: Devolución (+)
- `adjustment`: Ajuste manual (+/-)

**Ejemplo de gasto**:
```sql
INSERT INTO credit_transactions (user_id, amount, type, related_entity_type, related_entity_id)
VALUES ('user-uuid', -10, 'spend', 'historical_report', 'report-uuid');
```

---

### 3.6 Specialized Reports (3 tablas)

#### exploration_investigations
**Propósito**: Wizard de exploración UC-F11  
**Volumen**: ~3k+ registros esperados  
**RLS**: Usuario solo ve sus propias investigaciones

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `config` | JSONB | `{image_count, date_range, include_climate, include_ndvi}` |
| `result_hash` | VARCHAR | SHA-256 del PDF generado (verificabilidad) |
| `credits_used` | INT | Créditos debitados al completar |

**Ejemplo `config`**:
```json
{
  "image_count": 12,
  "date_range_months": 36,
  "include_climate": true,
  "include_ndvi": true,
  "visualization_type": "NBR"
}
```

#### burn_certificates
**Propósito**: Certificados legales verificables (UC-F10)  
**Volumen**: ~1k+ registros esperados  
**Security**: `data_hash` previene alteración de `snapshot_data`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `snapshot_data` | TEXT | JSON congelado del estado del fire_event |
| `certificate_number` | VARCHAR | Formato: `FG-CERT-2024-000123` |
| `verification_url` | VARCHAR | URL pública para verificar hash |

**Flujo de verificación**:
1. Usuario presenta certificado con número + hash
2. Tercero accede a `/api/v1/certificates/verify/{certificate_number}`
3. Backend compara hash almacenado vs. claim
4. Retorna `valid: true/false`

---

### 3.7 Vegetation Monitoring (2 tablas)

#### vegetation_monitoring
**Propósito**: Time series de NDVI post-incendio (UC-F12)  
**Volumen**: ~50k+ registros  
**Frecuencia**: Mensual durante 36 meses post-extinción

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `baseline_ndvi` | REAL | NDVI pre-incendio (referencia) |
| `recovery_percentage` | REAL | `(ndvi_mean / baseline_ndvi) * 100` |
| `human_activity_detected` | BOOL | Detección de cambio de uso |

#### land_use_changes
**Propósito**: Detección de cambios post-incendio (UC-F12)  
**Volumen**: ~5k+ registros  
**Trigger**: `recovery_percentage` baja + clasificación cambia

**Tipos de cambio**:
- `agriculture`: Conversión a agricultura
- `urban_development`: Urbanización
- `logging`: Tala
- `natural_recovery`: Recuperación natural

---

### 3.8 System Administration (4 tablas)

#### system_parameters
**Propósito**: Configuración dinámica del sistema  
**Ejemplos**:
```sql
-- Hard caps FinOps
audit_search_radius_max: 5000  -- meters
dashboard_page_size_max: 100
h3_max_cells_per_query: 10000
gee_daily_request_limit: 50000

-- Workers
carousel_batch_size: 15
closure_report_min_area_hectares: 10
```

#### audit_events
**Propósito**: Audit trail inmutable  
**RLS**: Solo admin  
**Retención**: Indefinida

**Acciones registradas**:
- `system.parameter.update`
- `user.role.change`
- `fire_event.manual_merge`
- `certificate.issue`

#### idempotency_keys
**Propósito**: Prevenir operaciones duplicadas  
**Endpoints críticos**:
- `POST /api/v1/reports/judicial`
- `POST /api/v1/reports/historical`
- `POST /api/v1/certificates`
- `POST /api/v1/payments/create-preference`

**Expiración**: 24 horas (auto-cleanup via Celery)

---

## 4. Materialized Views

### h3_recurrence_stats
**Propósito**: Agregaciones por celda H3 para heatmaps (UC-F05)  
**Refresh**: Diario @ 02:00 ART vía Celery Beat

```sql
CREATE MATERIALIZED VIEW h3_recurrence_stats AS
SELECT
    h3_index,
    COUNT(DISTINCT id) AS event_count,
    COUNT(DISTINCT EXTRACT(YEAR FROM start_date)) AS years_with_fires,
    AVG(estimated_area_hectares) AS avg_area,
    MAX(max_frp) AS max_frp_ever,
    -- Clasificación de recurrencia
    CASE
        WHEN COUNT(*) / 5.0 < 1 THEN 'low'
        WHEN COUNT(*) / 5.0 BETWEEN 1 AND 3 THEN 'medium'
        ELSE 'high'
    END AS recurrence_class
FROM fire_events
WHERE h3_index IS NOT NULL
GROUP BY h3_index;

CREATE INDEX idx_h3_recurrence_h3 ON h3_recurrence_stats(h3_index);
```

### fire_stats
**Propósito**: KPIs pre-calculados por provincia/mes  
**Columnas**: `province`, `year_month`, `total_fires`, `total_hectares`, `avg_frp`, `max_frp`

### fire_event_quality_metrics
**Propósito**: Scores de confiabilidad pre-calculados (UC-F04)  
**Columnas**: `fire_event_id`, `reliability_score`, `classification`, `data_completeness`

**Fórmula**:
```
reliability_score = 
    (detections_confidence * 0.40) +
    (imagery_quality * 0.20) +
    (climate_availability * 0.20) +
    (independent_detections * 0.20)
```

---

## 5. Índices Espaciales y Performance

### Índices GiST (PostGIS)

```sql
-- fire_events
CREATE INDEX idx_fire_events_centroid ON fire_events USING GIST (centroid);
CREATE INDEX idx_fire_events_perimeter ON fire_events USING GIST (perimeter);

-- protected_areas
CREATE INDEX idx_protected_areas_boundary ON protected_areas USING GIST (boundary);
CREATE INDEX idx_protected_areas_simplified ON protected_areas USING GIST (simplified_boundary);

-- fire_detections
CREATE INDEX idx_fire_detections_location ON fire_detections USING GIST (location);
```

### Índices H3 (BIGINT)

```sql
CREATE INDEX idx_fire_events_h3 ON fire_events(h3_index) WHERE h3_index IS NOT NULL;
CREATE INDEX idx_fire_detections_h3 ON fire_detections(h3_index) WHERE h3_index IS NOT NULL;
```

**Queries optimizadas**:
```sql
-- Recurrence heatmap
SELECT * FROM h3_recurrence_stats WHERE h3_index = ANY(h3_polyfill(bbox_polygon, 8));

-- Nearby fires
SELECT * FROM fire_events WHERE h3_index IN (
    SELECT h3_k_ring(h3_lat_lng_to_cell(lat, lng, 8), 2)
);
```

---

## 6. Row Level Security (RLS)

### Ejemplo: user_saved_filters

```sql
-- Solo el dueño puede ver sus filtros
CREATE POLICY user_saved_filters_select_own ON user_saved_filters
    FOR SELECT
    USING (auth.uid() = user_id);

-- Solo el dueño puede insertar
CREATE POLICY user_saved_filters_insert_own ON user_saved_filters
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Solo el dueño puede actualizar
CREATE POLICY user_saved_filters_update_own ON user_saved_filters
    FOR UPDATE
    USING (auth.uid() = user_id);
```

### Bypass para Admin

```sql
-- Admins pueden ver todo
CREATE POLICY admin_all_access ON user_saved_filters
    FOR ALL
    USING (
        (SELECT role FROM users WHERE id = auth.uid()) = 'admin'
    );
```

**Tablas con RLS habilitado** (todas sensibles):
- `user_saved_filters`
- `user_credits`
- `credit_transactions`
- `payment_requests`
- `payment_webhook_logs` (admin-only)
- `exploration_investigations`
- `land_use_audits`
- `citizen_reports`

---

## 7. Migraciones Clave

| Migración | Descripción |
|-----------|-------------|
| `004_add_h3_index_to_fire_events.sql` | Añade columna `h3_index BIGINT` |
| `007_create_h3_recurrence_stats.sql` | Materialized view para UC-F05 |
| `008_create_user_saved_filters.sql` | T1.7 preferencias de usuario |
| `009_extend_fire_episodes_columns.sql` | Añade `dnbr_severity`, `slides_data` |
| `012_align_fire_pipeline_uc_f08r.sql` | UC-F08 carousel completado |
| `014_create_exploration_investigations.sql` | UC-F11 wizard |
| `015_exploration_investigations_rls.sql` | RLS policies para investigations |
| `2026_02_01_add_fire_episodes.sql` | UC-F13 episodios y N:M |
| `2026_02_04_payment_tables.sql` | Sistema de pagos MercadoPago |

---

## 8. Constraints Críticos

### CHECK Constraints

```sql
-- Prohibición solo 30 o 60 años
ALTER TABLE protected_areas ADD CONSTRAINT prohibition_years_valid
    CHECK (prohibition_years IN (30, 60));

-- Créditos nunca negativos
ALTER TABLE user_credits ADD CONSTRAINT balance_non_negative
    CHECK (balance >= 0);

-- Parámetros de clustering razonables
ALTER TABLE clustering_versions ADD CONSTRAINT epsilon_km_range
    CHECK (epsilon_km > 0 AND epsilon_km <= 100);
```

### UNIQUE Constraints

```sql
-- Un solo registro de créditos por usuario
ALTER TABLE user_credits ADD CONSTRAINT user_credits_user_id_unique UNIQUE (user_id);

-- Referencias externas MercadoPago únicas
ALTER TABLE payment_requests ADD CONSTRAINT external_reference_unique UNIQUE (external_reference);

-- Certificate numbers únicos
ALTER TABLE burn_certificates ADD CONSTRAINT certificate_number_unique UNIQUE (certificate_number);
```

---

## 9. Resumen de Volumen y Rendimiento

| Tabla | Volumen Actual | Crecimiento/Mes | Queries/Día | Performance Target |
|-------|----------------|-----------------|-------------|-------------------|
| `fire_detections` | 100k+ | +10k | ~100 | < 100ms (indexed) |
| `fire_events` | 10k+ | +500 | ~5000 | < 50ms (indexed) |
| `fire_episodes` | 2k+ | +100 | ~500 | < 50ms |
| `protected_areas` | 1k | +5 (rare) | ~1000 | < 10ms (cached) |
| `satellite_images` | 20k+ | +2k | ~200 | < 100ms |
| `user_credits` | 2k+ | +50 | ~500 | < 10ms (PK lookup) |
| `h3_recurrence_stats` (MV) | 50k+ cells | refresh diario | ~1000 | < 20ms |

**Total DB size**: ~450MB / 500MB Supabase limit (90% capacity)  
**Mitigación**: Particionado + archivado a Parquet

---

## Apéndices

### A. Enums Documentados

```sql
-- fire_events.status
'active' | 'controlled' | 'monitoring' | 'extinguished'

-- fire_episodes.status
'active' | 'monitoring' | 'extinct' | 'closed'

-- protected_areas.category
'national_park' | 'national_reserve' | 'natural_monument' | ...

-- payment_requests.status
'pending' | 'approved' | 'rejected' | 'expired' | 'refunded'

-- credit_transactions.type
'purchase' | 'grant' | 'spend' | 'refund' | 'expiration' | 'adjustment'

-- exploration_investigations.investigation_type
'historical' | 'judicial'

-- exploration_investigations.status
'draft' | 'submitted' | 'processing' | 'completed' | 'failed'
```

### B. JSONB Schema Examples

**fire_events.slides_data**:
```json
[
  {
    "image_type": "SWIR",
    "url": "https://storage.googleapis.com/.../thumb.png",
    "gee_system_index": "20240215T141059_...",
    "bands_config": {"bands": ["B12", "B8A", "B4"], "min": 0, "max": 4000},
    "cloud_coverage": 12.5,
    "acquisition_date": "2024-02-15"
  }
]
```

**exploration_investigations.config**:
```json
{
  "image_count": 12,
  "date_range_months": 36,
  "include_climate": true,
  "include_ndvi": true,
  "visualization_type": "NBR",
  "custom_bands": {
    "before": ["B8", "B4", "B3"],
    "after": ["B12", "B11", "B8A"]
  }
}
```

---

**Documento generado**: Febrero 2026  
**Próxima actualización**: Tras completar migraciones pendientes (Phase 4-6)
