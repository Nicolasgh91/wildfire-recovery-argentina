# UC-F12 Data Flow Processing Diagram

This ASCII diagram illustrates the complete data pipeline from raw FIRMS data ingestion to final frontend display, showing all processing steps, tables, and transformations.

## Complete Data Flow Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              DATA INGESTION LAYER                                  │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────┐    ┌─────────────────────────────────────┐    ┌─────────────────┐
│   FIRMS RAW     │    │     HISTORICAL DATA FILES           │    │  CLIMATE DATA   │
│   DETECTIONS    │    │                                     │    │  (Open-Meteo)   │
│                 │    │ ┌─────────────────────────────────┐ │    │                 │
│ 2015-01-01 to   │    │ │ 0_historical_detections_2015_2026 │ │    │ Temperature,    │
│ 2025-10-31      │    │ │ .csv (185MB)                     │ │    │ Humidity, Wind  │
│                 │    │ └─────────────────────────────────┘ │    │ Precipitation   │
│ • latitude      │    │ ┌─────────────────────────────────┐ │    │                 │
│ • longitude     │    │ │ 1_2025-11-01_2026-01-25.csv     │ │    │                 │
│ • brightness    │    │ │ 2_fire-detections-25-01-2026... │ │    │                 │
│ • confidence    │    │ │ 3_fire-detections-31-01-2026... │ │    │                 │
│ • acq_date      │    │ │ 4_fire-detections-16-02-2026... │ │    │                 │
│ • satellite     │    │ └─────────────────────────────────┘ │    │                 │
└─────────┬───────────┘    └─────────────────────────────────────┘    └─────────┬───────┘
          │                                                            │
          │ 1. ETL PROCESSING                                           │ 2. CLIMATE ETL
          ▼                                                            ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                            PROCESSING LAYER                                           │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────┐    ┌─────────────────────────────────────┐
│         FIRE DETECTION              │    │        CLIMATE PROCESSING           │
│         CLUSTERING                  │    │                                     │
│                                     │    │ ┌─────────────────────────────────┐ │
│ • Spatial clustering (ST-DBSCAN)    │    │ │ Open-Meteo API → climate_data    │ │
│ • Temporal window (hours)          │    │ │                                 │ │
│ • Create fire_events               │    │ │ • temperature_2m                │ │
│                                     │    │ • relative_humidity_2m          │ │
│ INPUT:                              │    │ • wind_speed_10m                │ │
│ • Raw FIRMS detections             │    │ • precipitation                  │ │
│ • Geographic proximity             │    │ • fire_weather_index             │ │
│ • Time proximity                   │    │                                 │ │
│                                     │    │ └─────────────────────────────────┘ │
│ OUTPUT:                             │    │                                     │
│ • fire_events table                │    │ ASSOCIATION:                       │
│ • fire_detections table            │    │ • fire_climate_associations       │ │
└─────────┬───────────────────────────┘    └─────────────────────────────────────┘
          │
          │ 3. FIRE EVENT CREATION
          ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              DATABASE LAYER                                          │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                fire_events                                         │
│                                                                                     │
│ • id (UUID)                              • centroid (geometry)                      │
│ • start_date, end_date                  • perimeter (geometry)                     │
│ • estimated_area_hectares               • province, department                     │
│ • total_detections                      • is_significant                           │
│ • avg_frp, max_frp, sum_frp             • status (active/monitoring/extinct)      │
│ • avg_confidence                        • created_at, updated_at                  │
│ • last_gee_image_id                     • clustering_version_id                   │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ 4. WORKER TRIGGER
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                            WORKER PROCESSING LAYER                                    │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              CELERY WORKERS                                          │
│                                                                                     │
│ ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────────────────────────┐ │
│ │   worker-vae    │   │  celery-beat    │   │         worker-analysis             │ │
│ │                 │   │                 │   │                                     │ │
│ │ • Queue: vae    │   │ • Monthly       │   │ • Queue: analysis                  │ │
│ │ • Recovery      │   │   schedule      │   │ • Other analysis tasks             │ │
│ │ • Land Use      │   │ • Auto-trigger  │   │                                     │ │
│ │ • Temporal      │   │   batch jobs    │   │                                     │ │
│ └─────────────────┘   └─────────────────┘   └─────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ 5. SATELLITE IMAGERY PROCESSING
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           GOOGLE EARTH ENGINE                                       │
│                                                                                     │
│ INPUT:                                                                              │
│ • fire_event centroid (lat, lon)                                                   │
│ • bbox (±0.01° ~ 1km buffer)                                                       │
│ • fire_date                                                                        │
│ • analysis_date                                                                    │
│                                                                                     │
│ SATELLITE DATA:                                                                     │
│ • Sentinel-2 SR (Surface Reflectance)                                              │
│ • Bands: B2 (Blue), B3 (Green), B4 (Red), B8 (NIR)                               │
│ • Cloud masking (S2_CLOUD_PROBABILITY)                                             │
│ • NDVI calculation: (NIR - Red) / (NIR + Red)                                      │
│                                                                                     │
│ PROCESSING:                                                                         │
│ • Baseline NDVI (pre-fire: 6-12 months before)                                     │
│ • Current NDVI (analysis date or latest available)                                  │
│ • Time series (monthly intervals)                                                   │
│ • Cloud cover filtering                                                            │
│                                                                                     │
│ OUTPUT:                                                                             │
│ • NDVI values (mean, min, max, std)                                               │
│ • Image metadata (cloud cover, acquisition date)                                  │
│ • Visualization parameters                                                         │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ 6. VAE ANALYSIS ENGINE
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           VAE SERVICE PROCESSING                                    │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────┐
│                        RECOVERY ANALYSIS (UC-06)                                    │
│                                                                                     │
│ INPUT:                                                                              │
│ • Baseline NDVI                                                                     │
│ • Current NDVI                                                                      │
│ • Months after fire                                                                │
│                                                                                     │
│ CALCULATIONS:                                                                       │
│ • ndvi_change = current_ndvi - baseline_ndvi                                       │
│ • recovery_percentage = (current_ndvi / baseline_ndvi) * 100                        │
│ • expected_recovery = EXPECTED_RECOVERY[months_after]                             │
│ • recovery_deviation = recovery_percentage - expected_recovery                      │
│                                                                                     │
│ CLASSIFICATION:                                                                      │
│ • RecoveryStatus (NOT_STARTED → FULL_RECOVERY)                                     │
│ • Anomaly detection (sudden_drop, no_recovery, geometric_pattern)                  │
│ • AnomalyType (NONE, SUDDEN_DROP, NO_RECOVERY, GEOMETRIC_PATTERN, RAPID_GREENING) │
│                                                                                     │
│ OUTPUT: RecoveryAnalysis                                                            │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ 7. LAND USE CHANGE DETECTION (UC-08)
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                      LAND USE CHANGE ANALYSIS                                      │
│                                                                                     │
│ INPUT:                                                                              │
│ • Baseline NDVI                                                                     │
│ • Current NDVI                                                                      │
│ • NDVI change                                                                       │
│ • Months after fire                                                                │
│ • Area hectares                                                                     │
│                                                                                     │
│ PATTERN ANALYSIS:                                                                   │
│ • Geometric index (pattern regularity)                                             │
│ • Texture change                                                                   │
│ • NDVI persistence patterns                                                        │
│                                                                                     │
│ CLASSIFICATION:                                                                      │
│ • LandUseChangeType (NATURAL_RECOVERY, BARE_SOIL, AGRICULTURE,                    │
│   CONSTRUCTION, ROADS, MINING, DEFORESTATION, UNCERTAIN)                           │
│ • Severity (LOW, MEDIUM, HIGH, CRITICAL)                                            │
│ • is_potential_violation (true for construction/agriculture/mining/deforestation) │
│                                                                                     │
│ OUTPUT: LandUseAnalysis                                                             │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ 8. DATA PERSISTENCE
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                            OUTPUT TABLES                                            │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────┐
│                          vegetation_monitoring                                      │
│                                                                                     │
│ • fire_event_id (FK)                        • monitoring_date (date)               │
│ • satellite_image_id (FK)                    • months_after_fire (int)              │
│ • ndvi_mean, ndvi_min, ndvi_max              • baseline_ndvi (real)                │
│ • ndvi_std_dev                               • recovery_percentage (real)           │
│ • land_use_classification                    • human_activity_detected (bool)       │
│ • classification_confidence                  • activity_type, activity_confidence   │
│ • created_at, updated_at                     • UNIQUE(fire_event_id, monitoring_date) │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           land_use_changes                                          │
│                                                                                     │
│ • fire_event_id (FK)                        • change_detected_at (date)            │
│ • monitoring_record_id (FK)                  • months_after_fire (int)              │
│ • change_type (enum)                         • change_severity (enum)               │
│ • affected_area_hectares (double)            • is_potential_violation (bool)        │
│ • violation_confidence                       • status (pending_review/reviewed)      │
│ • before_image_id, after_image_id (FK)       • notes (text)                        │
│ • created_at, updated_at                     • UNIQUE(fire_event_id, change_detected_at)│
└─────────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ 9. API ENDPOINTS
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              API LAYER                                              │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────┐
│                        MONITORING ENDPOINTS                                         │
│                                                                                     │
│ GET /api/v1/monitoring/recovery/summary                                             │
│ • Total events analyzed                                                            │
│ • Recovery status distribution                                                     │
│ • Violations detected                                                              │
│                                                                                     │
│ GET /api/v1/monitoring/recovery/{fire_event_id}                                    │
│ • Baseline NDVI                                                                    │
│ • Current NDVI                                                                     │
│ • Recovery percentage                                                             │
│ • Recovery status                                                                 │
│ • Monthly monitoring data[]                                                        │
│ • Anomaly detected                                                                │
│                                                                                     │
│ POST /api/v1/monitoring/recovery/trigger                                           │
│ • Manual trigger for specific fire_event_id                                        │
│ • Admin-only endpoint                                                             │
│                                                                                     │
│ GET /api/v1/monitoring/land-use/{fire_event_id}                                    │
│ • Change detection results                                                         │
│ • Violation status                                                                │
│ • Affected area                                                                   │
│ • Recommended actions                                                             │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ 10. FRONTEND DISPLAY
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                            FRONTEND COMPONENTS                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────┐
│                          RecoveryPanel Component                                     │
│                                                                                     │
│ DISPLAY ELEMENTS:                                                                   │
│ • RecoveryStatusBadge (colored status indicator)                                    │
│ • Metric cards:                                                                     │
│   - Baseline NDVI                                                                  │
│   - Current NDVI                                                                   │
│   - Recovery %                                                                     │
│ • NDVI trend chart (monthly time series)                                            │
│ • Land use change cards (if violations detected)                                   │
│ • Empty state ("Análisis de recuperación pendiente")                               │
│                                                                                     │
│ AUTHENTICATION GATE:                                                               │
│ • Only visible to authenticated users (isAuthenticated)                              │
│ • Hidden on episode detail pages (isEpisodeDetail)                                │
│ • Only shows on fire event detail pages (/fires/{id})                             │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────┐
│                         INTEGRATION POINTS                                          │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           Home Feed Integration                                     │
│                                                                                     │
│ • RecoveryStatusBadge on fire episode cards                                        │
│ • Filter by recovery status                                                        │
│ • Quick access to detailed analysis                                                │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────┐
│                            Map Integration                                          │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────┐
│ • Special markers for events with is_potential_violation = true                    │
│ • Red alert icons for detected violations                                           │
│ • Click to view detailed land use change analysis                                   │
└─────────────────────────────────────────────────────────────────────────────────────┘

## PROCESSING SUMMARY

### Data Volume:
- **Input**: 185MB FIRMS data (2015-2025)
- **Events**: Thousands of fire events
- **Processing**: 2-3 GEE requests per event
- **Output**: vegetation_monitoring + land_use_changes tables

### Key Transformations:
1. **Raw Detections** → **Fire Events** (spatio-temporal clustering)
2. **Fire Events** → **NDVI Analysis** (Sentinel-2 + GEE)
3. **NDVI Values** → **Recovery Metrics** (VAE calculations)
4. **NDVI Changes** → **Land Use Classification** (pattern detection)
5. **Analysis Results** → **Database Records** (worker persistence)
6. **Database Records** → **API Responses** (REST endpoints)
7. **API Responses** → **UI Components** (React frontend)

### Quality Controls:
- UNIQUE constraints prevent duplicate processing
- RLS policies ensure data security
- Circuit breaker prevents GEE overload
- Rate limiting respects API quotas
- Retry logic handles transient failures
