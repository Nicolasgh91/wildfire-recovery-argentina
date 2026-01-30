# 📋 ForestGuard API - Complete Use Cases

## Executive summary

This document details the **13 main use cases** that the ForestGuard API is designed to solve. Each use case is linked to real needs for environmental oversight, institutional transparency, and defense of Argentina's natural heritage under the framework of Law 26.815 (Fire Management).

---

## 🔴 Category: Oversight and law enforcement

### UC-01: Post-fire land use change audit

**Description:**  
Determine if a specific plot was affected by a fire and if there is a legal prohibition to change its land use (subdivision, agriculture, construction).

**Primary actor:** Notaries, municipal inspectors, land buyers

**Main flow:**
1. User inputs geographic coordinates or cadastral ID
2. System searches for fire events within a 500m radius (configurable)
3. System determines if the plot intersects with a protected area
4. System calculates prohibition date according to Law 26.815 Art. 22 bis:
   - 60 years for native forests and protected areas
   - 30 years for agricultural zones/grasslands
5. System returns:
   - List of historical fires
   - Prohibition dates
   - Pre/post fire satellite images
   - Current legal status

**Data required:**
- `fire_events` (fire events)
- `protected_areas` (protected areas)
- `fire_protected_area_intersections` (spatial intersections)
- `satellite_images` (visual evidence)

**Endpoint:**
```
GET /api/v1/audit/land-use?lat={lat}&lon={lon}&radius={meters}
```

**Example response:**
```json
{
  "location": {"lat": -27.4658, "lon": -58.8346},
  "fires_found": 2,
  "earliest_fire_date": "2015-08-22",
  "prohibition_until": "2075-08-22",
  "is_prohibited": true,
  "protected_area": {
    "name": "Parque Nacional Chaco",
    "category": "national_park"
  },
  "evidence": [
    {
      "fire_id": "uuid-123",
      "date": "2015-08-22",
      "image_url": "https://r2.forestguard.ar/fires/uuid-123/post_fire.jpg"
    }
  ]
}
```

**Success criteria:**
- ✅ Spatial precision < 500m
- ✅ Response in < 2 seconds
- ✅ Includes verifiable visual evidence

---

### UC-02: Forensic judicial report generation

**Description:**  
Produce a technical report with climatic context, event chronology, and satellite evidence for use in judicial processes.

**Primary actor:** Judicial experts, environmental prosecutors, lawyers

**Main flow:**
1. User requests a report for a specific fire (ID or coordinates)
2. System collects:
   - Satellite detection data (VIIRS/MODIS)
   - Climatic conditions on the event day (temperature, wind, drought)
   - Before/after satellite images
   - Fire history in the area (recurrence)
3. System generates structured PDF with:
   - Event chronology
   - Propagation map
   - Analysis of propitious conditions
   - "Key Findings" section
4. PDF includes SHA256 hash for integrity verification

**Data required:**
- `fire_detections` (individual detections)
- `fire_events` (aggregated event)
- `climate_data` (meteorological context)
- `satellite_images` (visual evidence)
- `data_source_metadata` (source transparency)

**Endpoint:**
```
POST /api/v1/reports/judicial
Content-Type: application/json

{
  "fire_event_id": "uuid-456",
  "report_type": "full_forensic",
  "language": "en"
}
```

**Response:**
```json
{
  "report_id": "FG-REPORT-2025-001",
  "pdf_url": "https://r2.forestguard.ar/reports/FG-REPORT-2025-001.pdf",
  "verification_hash": "a3f5b8c9d2e1...",
  "generated_at": "2025-01-24T14:30:00Z",
  "valid_until": "2026-01-24T14:30:00Z"
}
```

**Success criteria:**
- ✅ Includes disclaimers about data limitations
- ✅ Cites sources accurately (NASA FIRMS, ERA5, Sentinel-2)
- ✅ Format admissible in court

---

### UC-07: Land legal condition certification

**Description:**  
Issue a verifiable digital certificate indicating whether a land is legally exploitable or has restrictions due to previous fires.

**Primary actor:** Real estate agencies, notaries, buyers, banks (for mortgages)

**Main flow:**
1. User requests certificate for specific coordinates
2. System executes full audit (UC-01)
3. System generates certificate with:
   - Unique certificate number
   - QR code for online verification
   - Clear legal status: `clear`, `prohibited`, `restricted`
   - Certificate validity (e.g., 90 days)
   - SHA256 hash of content
4. Certificate is saved in `land_certificates` for audit

**Data required:**
- `land_use_audits` (query log)
- `fire_events`, `protected_areas` (analysis)
- `land_certificates` (certificate registry)

**Endpoint:**
```
POST /api/v1/certificates/request
Content-Type: application/json

{
  "latitude": -34.6037,
  "longitude": -58.3816,
  "cadastral_id": "BA-123-456-789",
  "requester_email": "escribano@example.com"
}
```

**Response:**
```json
{
  "certificate_number": "FG-CERT-2025-001234",
  "legal_status": "prohibited_recent_fire",
  "is_legally_exploitable": false,
  "prohibition_expires_on": "2054-03-15",
  "pdf_url": "https://forestguard.ar/certificates/FG-CERT-2025-001234.pdf",
  "qr_code_url": "https://forestguard.ar/verify/FG-CERT-2025-001234",
  "verification_hash": "b7e4f3a2...",
  "issued_at": "2025-01-24T15:00:00Z",
  "valid_until": "2025-04-24T15:00:00Z"
}
```

**Success criteria:**
- ✅ Publicly verifiable certificate
- ✅ Anti-forgery hash
- ✅ Clear and non-technical language
- ✅ Accepted by financial institutions

---

## 🟡 Category: Detection and alerts

### UC-03: Recurrence and pattern analysis

**Description:**  
Identify zones with recurrent fires to detect suspicious patterns of systematic land use change.

**Primary actor:** Environmental NGOs, specialized prosecutors, researchers

**Main flow:**
1. User defines area of interest (polygon or radius)
2. System searches for all fires in the last N years
3. System calculates:
   - Fire density per km²
   - Temporality (seasonal vs off-season)
   - Overlaps (fires in the same area)
4. System classifies zones as:
   - `low_risk`: < 1 fire every 5 years
   - `medium_risk`: 1-3 fires every 5 years
   - `high_risk`: > 3 fires every 5 years (suspicious)
5. Generates recurrence heatmap

**Data required:**
- `fire_events` (full history)
- `fire_detections` (for fine temporal analysis)

**Endpoint:**
```
GET /api/v1/analysis/recurrence?bbox={minLon},{minLat},{maxLon},{maxLat}&years=10
```

**Success criteria:**
- ✅ Identifies zones with > 3 fires/5 years
- ✅ Clear visualization of patterns
- ✅ Exportable as GeoJSON for GIS

---

### UC-04: Early warning for park carrying capacity

**Description:**  
Correlate visitor influx in parks with fire risk to issue preventive alerts.

**Primary actor:** APN (National Parks Administration), rangers

**Main flow:**
1. System receives visitor data (tickets sold, estimates)
2. System calculates carrying capacity vs real occupancy
3. System cross-references with:
   - Fire history in the same season
   - Current climatic conditions (drought, wind)
4. If capacity > 80% + high risk conditions → Alert
5. Notification to rangers to reinforce surveillance

**Data required:**
- `protected_areas` (parks)
- `fire_events` (history)
- `climate_data` (current conditions)
- External data: visitor influx (APN API or manual)

**Endpoint:**
```
POST /api/v1/alerts/park-capacity
Content-Type: application/json

{
  "park_id": "uuid-park-nahuel-huapi",
  "visitor_count": 1500,
  "date": "2025-01-15"
}
```

**Success criteria:**
- ✅ Alert issued with > 12 hours anticipation
- ✅ False positive rate < 20%

---

### UC-08: Post-fire land use change detection

**Description:**  
Automatically monitor burnt areas to detect human activity (construction, agriculture, mining) that violates the legal prohibition.

**Primary actor:** Environmental prosecutors, NGOs, vigilant citizens

**Main flow:**
1. System (VAE Service) processes monthly images of burnt areas
2. Calculates NDVI and detects anomalies:
   - Drastic drop in NDVI without recovery → `bare_soil`
   - Geometric patterns → `construction_detected`, `roads_detected`
   - Grid vegetation → `agriculture_detected`
3. If positive detection → Creates record in `land_use_changes`
4. System notifies human reviewers
5. If confirmed → Generates alert to authorities

**Data required:**
- `fire_events` (base events)
- `vegetation_monitoring` (monthly NDVI)
- `satellite_images` (pre/post comparison)
- `land_use_changes` (detections)

**Endpoint (Automatic Worker):**
```
POST /api/v1/workers/detect-land-use-change
Content-Type: application/json

{
  "fire_event_id": "uuid-789",
  "monitoring_month": 6
}
```

**Response:**
```json
{
  "change_detected": true,
  "change_type": "construction_detected",
  "confidence": 0.85,
  "affected_area_hectares": 12.5,
  "before_image": "https://r2.forestguard.ar/...",
  "after_image": "https://r2.forestguard.ar/...",
  "is_potential_violation": true
}
```

**Success criteria:**
- ✅ Automatic detection > 75% of real cases
- ✅ False positives < 30%
- ✅ Alert generated in < 48 hours from image acquisition

---

### UC-13: Fire grid visualization and filtering

**Description:**  
Build a grid/list page to query registered fires and filter by key attributes, supporting typical queries (by province, protected area, dates, and status).

**Primary actor:** General users, analysts, operators

**Main flow:**
1. User accesses the "Fires" section
2. Views paginated grid with key columns:
   - Event ID / Detection ID
   - Last detection / Start date
   - Province
   - Protected area (yes/no + name)
   - Status/Category
   - Confidence (normalized)
   - Severity (FRP total, detections, estimated area)
3. Applies filters:
   - Province
   - Category/Status (e.g., Suspected/Confirmed/Controlled)
   - Protected Area
   - Date range
   - "Current fires only"
4. Sorts by date/severity
5. Opens fire detail (optional) to view timeline/map

**Business rules:**
- RB-01: Grid must paginate from DB (not load everything in memory)
- RB-02: Filters must translate to efficient queries (indexes)
- RB-03: "Current fires" defined by time window (e.g., detection in last N days) or `is_active` field

**Data required:**
- `fire_events` (consolidated events)
- `fire_detections` (aggregated detections)

**Endpoint:**
```
GET /api/v1/fires?province[]={province}&protected_area_id={id}&from={date}&to={date}&status={status}&active={bool}&min_confidence={float}&page={n}&page_size={n}&sort={field}
GET /api/v1/fires/{id}
GET /api/v1/fires/export?... (optional CSV/XLSX)
```

**Success criteria:**
- ✅ Performance: response < 1-2s with pagination
- ✅ Observability: logs for slow queries
- ✅ Security: protect administrative filters by role

---

## 🟢 Category: Analysis and reports

### UC-05: Historical trends and projections

**Description:**  
Analyze temporal fire patterns to identify long-term trends and emerging risk zones.

**Primary actor:** Researchers, territorial planners, media

**Main flow:**
1. User selects time range (e.g., 2004-2024)
2. User defines filters:
   - Province/region
   - Area type (protected, agricultural, urban)
   - Season (winter, summer)
3. System calculates:
   - Number of fires per year
   - Total affected hectares
   - Average intensity (FRP)
   - Spatial distribution (hotspot migration)
4. System generates:
   - Time series charts
   - Spatial evolution maps
   - Basic trend prediction (linear regression)

**Data required:**
- `fire_events` (full history 2004-2024)
- `protected_areas` (zone classification)

**Endpoint:**
```
GET /api/v1/analysis/trends?start_year=2004&end_year=2024&province=Corrientes
```

**Success criteria:**
- ✅ Interactive visualization
- ✅ Exportable as CSV/JSON
- ✅ Includes confidence intervals in projections

---

### UC-06: Vegetation recovery tracking (reforestation)

**Description:**  
Monitor natural recovery of burnt areas using vegetation indices (NDVI) for 36 months post-fire.

**Primary actor:** Ecologists, reforestation NGOs, APN

**Main flow:**
1. System identifies burnt areas
2. System (VAE Service) processes monthly Sentinel-2 image
3. Calculates average NDVI of the burnt area
4. Compares with pre-fire NDVI (baseline) detecting recovery rate
5. Calculates % recovery
6. Stores in `vegetation_monitoring`
7. Generates temporal evolution chart

**Data required:**
- `fire_events` (base area)
- `satellite_images` (monthly images)
- `vegetation_monitoring` (NDVI time series)

**Endpoint:**
```
GET /api/v1/monitoring/recovery/{fire_event_id}
```

**Response:**
```json
{
  "fire_event_id": "uuid-456",
  "fire_date": "2023-08-15",
  "baseline_ndvi": 0.65,
  "monitoring_data": [
    {"month": 1, "date": "2023-09-15", "ndvi": 0.22, "recovery": 34},
    {"month": 6, "date": "2024-02-15", "ndvi": 0.48, "recovery": 74},
    {"month": 12, "date": "2024-08-15", "ndvi": 0.61, "recovery": 94}
  ]
}
```

**Success criteria:**
- ✅ Cloud-free images > 80% of months
- ✅ Detection of "non-recovery" (possible illegal use)

---

### UC-10: Data reliability assessment

**Description:**  
Provide quality and reliability metrics for each fire event for use in expert reports and scientific analysis.

**Primary actor:** Experts, researchers, data journalists

**Main flow:**
1. User queries specific event or set of events
2. System calculates "Reliability Score" (0-100) based on:
   - Average detection confidence (40%)
   - Satellite imagery availability (20%)
   - Climate data available (20%)
   - Number of independent detections (20%)
3. System classifies as: `high`, `medium`, `low` reliability
4. System exposes source metadata:
   - Spatial resolution (VIIRS 375m, Sentinel-2 10m)
   - Known limitations
   - Legal admissibility

**Data required:**
- `fire_event_quality_metrics` (view)
- `data_source_metadata` (source table)

**Endpoint:**
```
GET /api/v1/quality/fire-event/{fire_event_id}
```

**Response:**
```json
{
  "fire_event_id": "uuid-789",
  "reliability_score": 87,
  "reliability_class": "high",
  "metrics": {
    "satellite_sources": 2,
    "avg_confidence": 92,
    "total_detections": 5,
    "has_imagery": true,
    "has_climate_data": true
  },
  "data_sources": [
    {
      "name": "NASA_FIRMS_VIIRS",
      "resolution": "375m",
      "accuracy": "85%",
      "admissible_in_court": true
    }
  ],
  "limitations": [
    "Small fires < 14 hectares may not be detected",
    "Cloud cover may prevent optical imagery acquisition"
  ]
}
```

**Success criteria:**
- ✅ Total source transparency
- ✅ Reproducible and documented score
- ✅ Useful for legal defense

---

### UC-11: Historical report search and generation in protected areas

**Description:**  
Implement functionality to identify, validate, and monitor historical fire events in protected areas, with the capability to generate detailed PDF reports.

**Primary actor:** Rangers, Researchers, Enforcement authorities

**Main flow:**
1. User configures fire image search by time period.
2. User selects a specific protected area.
3. System shows the amount of areas affected by identified events.
4. User requests PDF report generation.
5. System obtains Pre-Fire images (low cloudiness, 30 days prior window).
6. System obtains Post-Fire images (configurable frequency daily/monthly/yearly, up to 1 year post-fire, max 12 images).
7. System (ERS) generates PDF including:
   - Image grid
   - Metadata, hash, and verification QR code
   - Project logo and official branding

**Data required:**
- `protected_areas`
- `sentinel_2_imagery` (via STAC Copernicus/Planetary Computer)
- `fire_events_metadata`

**Technical requirements:**
- **Image Quality**: Sufficient resolution to identify constructions, roads, vegetation (Sentinel-2 viable).
- **Efficiency**: Optimized lightweight queries and caching with TTL (Redis).
- **Storage**: Do not store heavy images/reports in DB, only metadata.

**Endpoint:**
```
POST /api/v1/reports/historical-fire
Content-Type: application/json

{
  "protected_area_id": "uuid-park-123",
  "date_range": {"start": "2023-01-01", "end": "2023-12-31"},
  "report_config": {
    "post_fire_frequency": "monthly",
    "max_images": 12
  }
}
```

**Success criteria:**
- ✅ Clear identification of elements on the ground
- ✅ PDF report generated with correct branding
- ✅ Efficient use of STAC API (images cropped to AOI)

---

### UC-12: Digital visitor registration for mountain shelters (Offline-first)

**Description:**  
Digitize the daily visitor registration (entries and overnight stays) in mountain shelters, replacing paper records with a **mobile-first**, **offline-first**, secure, and auditable system with automatic synchronization and statistics/export generation.

**Primary actor:** Shelter operators, APN administrators, auditors

**Main flow:**
1. Operator opens the app (web/PWA)
2. Selects "New Registration"
3. Completes:
   - shelter
   - Date (default: today)
   - Registration type: Day Entry / Overnight
4. Completes **group leader** data
5. Adds companions via a **dynamic list**:
   - Full name
   - Age or age range
   - Document (optional)
6. System automatically calculates total people
7. Saves the record:
   - If online → syncs with backend
   - If offline → saved locally (IndexedDB)
8. When connectivity is restored, system syncs automatically
9. Operator can edit the record **up to 30 minutes** after first sync
10. Administrator can query statistics and export data

**Business rules:**
- RB-01 (Offline-first): System must allow creating and storing records without connection
- RB-02 (Synchronization): Local records sync automatically when there's connectivity
- RB-03 (Limited editing): A record can only be edited up to **30 minutes** after `first_submitted_at`
- RB-04 (Audit): Every edit generates a historical revision
- RB-05 (Security): Access restricted by roles (RLS / JWT)
- RB-06 (Export): Data can be exported in CSV or XLSX

**Data required:**
- `shelters` (shelter catalog)
- `visitor_logs` (registration records)
- `visitor_log_companions` (companion details)
- `visitor_log_revisions` (edit history)

**Endpoints:**
```
POST /api/v1/visitor-logs
PATCH /api/v1/visitor-logs/{id} (validates 30-min window)
GET /api/v1/visitor-logs?shelter_id=&from=&to=
GET /api/v1/visitor-logs/export?from=&to=&province=&shelter_id= (CSV/XLSX)
GET /api/v1/shelters?province=&q=
```

**Frontend stack (Offline-first):**
- Vite + React + TypeScript
- Tailwind CSS (branding)
- TanStack Query (cache persistence + offline mutation queue)
- IndexedDB / LocalForage
- PWA (Service Worker, asset caching, installable)

**Success criteria:**
- ✅ Eliminates paper records
- ✅ Improves traceability and data quality
- ✅ Enables historical statistical analysis
- ✅ Foundation for correlation with environmental risk and emergencies

---

## 🔵 Category: Citizen participation

### UC-09: Citizen reporting support

**Description:**  
Allow citizens, NGOs, and communities to report suspicious activity in burnt areas and receive an automatic satellite evidence package.

**Primary actor:** Citizens, NGOs, indigenous communities, media

**Main flow:**
1. User accesses web form (anonymous or registered)
2. User marks location on map and describes:
   - Activity type (construction, clearing, etc.)
   - Date observed
   - Optional photos (uploaded to R2)
3. System automatically:
   - Searches historical fires in 1km radius
   - Searches nearby protected areas
   - Generates evidence package using Evidence Reporting Service (ERS):
     - Pre/post fire satellite images
     - Fire chronology
     - Legal status of the area
4. Report is registered in `citizen_reports`
5. System notifies reviewers (NGOs, authorities)
6. If verified → Marked as `forwarded_to_authorities`

**Data required:**
- `citizen_reports` (reports)
- `fire_events`, `protected_areas` (automatic cross-reference)
- `satellite_images` (evidence)

**Endpoint:**
```
POST /api/v1/reports/citizen/submit
Content-Type: application/json

{
  "latitude": -27.1234,
  "longitude": -55.4567,
  "report_type": "construction_in_prohibited_area",
  "description": "Soil movement and machinery observed in 2022 burnt zone",
  "observed_date": "2025-01-20",
  "reporter_email": "citizen@example.com",
  "is_anonymous": false
}
```

**Response:**
```json
{
  "report_id": "uuid-report-123",
  "status": "submitted",
  "evidence_package_url": "https://r2.forestguard.ar/reports/uuid-report-123/evidence.zip",
  "related_fires": 2,
  "related_protected_areas": ["Parque Provincial XYZ"],
  "created_at": "2025-01-24T16:00:00Z"
}
```

**Success criteria:**
- ✅ Simple form (< 5 minutes to complete)
- ✅ Evidence generated automatically in < 1 minute
- ✅ Anonymity option respected
- ✅ Integration with Telegram/WhatsApp channel for NGOs

---

## 📊 Use case matrix

| UC | Name | Priority | Complexity | Legal Impact | Social Impact |
|----|------|----------|------------|--------------|---------------|
| UC-01 | Anti-Loteo Audit | 🔴 HIGH | Medium | ⚖️ High | 🏘️ High |
| UC-02 | Judicial Report | 🔴 HIGH | High | ⚖️ Very High | 📜 Medium |
| UC-03 | Recurrence | 🟡 MEDIUM | Medium | ⚖️ Medium | 🔍 High |
| UC-04 | Early Warning | 🟡 MEDIUM | Low | ⚖️ Low | 🚨 Medium |
| UC-05 | Trends | 🟢 LOW | Medium | ⚖️ Low | 📊 High |
| UC-06 | Reforestation | 🟡 MEDIUM | High | ⚖️ Medium | 🌳 High |
| UC-07 | Certification | 🔴 HIGH | Medium | ⚖️ Very High | 💼 High |
| UC-08 | Land Use Change | 🔴 HIGH | Very High | ⚖️ High | 🚧 High |
| UC-09 | Reporting | 🟡 MEDIUM | Low | ⚖️ Medium | 🧑‍🤝‍🧑 Very High |
| UC-10 | Data Quality | 🔴 HIGH | Low | ⚖️ High | 🔬 Medium |
| UC-11 | Hist. Reports | 🟡 MEDIUM | Medium | ⚖️ Medium | 📊 High |
| UC-12 | Visitor Registration | 🟡 MEDIUM | Medium | ⚖️ Low | 🏔️ High |
| UC-13 | Fire Grid View | 🟢 LOW | Low | ⚖️ Low | 📋 Medium |

---

## 🎯 Implementation roadmap

### Phase 1: Core MVP (weeks 1-6)
- ✅ UC-01: Anti-Loteo Audit
- ✅ UC-02: Judicial Report
- ✅ UC-06: Reforestation (basic)
- ✅ UC-10: Data Quality
- ✅ UC-11: Historical Reports (MVP)
- ✅ UC-13: Fire Grid View (basic)

### Phase 2: Certification and alerts (weeks 7-8)
- ✅ UC-07: Legal Certification
- ✅ UC-09: Citizen Reporting
- ⚠️ UC-08: Land Use Change (basic rules)

### Phase 3: Post-MVP (after launch)
- 🔜 UC-03: Recurrence Analysis
- 🔜 UC-04: Building Capacity Alerts
- 🔜 UC-05: Historical Trends
- 🔜 UC-08: Land Use Change (advanced ML)
- 🔜 UC-11: Historical Reports (v2)
- 🔜 UC-12: Visitor Registration (PWA + offline)

---

## 📞 Contact and feedback

For new use case suggestions or improvements:
- GitHub Issues: `github.com/forestguard/api/issues`
- Email: `contact@forestguard.ar`
- Community: `discord.gg/forestguard`

---

**Version:** 4.0  
**Last updated:** 2026-01-29  
**Authors:** ForestGuard Team

