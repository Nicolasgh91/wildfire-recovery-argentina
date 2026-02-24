# UC-F12 VAE — Technical Debt & Deviations

> **Date:** 2026-02-24
> **Context:** Implementation of UC-F12 tasks from `3_UC_F12_technical_tasks_claude_code.md`

---

## Deviations from Task List

### TAREA 0.2: Complementary migration NOT created
- **Reason:** The existing migration `2026_02_23_uc_f12_vae_monitoring.sql` already covers ALL required elements: UNIQUE constraints (`uq_vm_event_date`, `uq_luc_event_date`), NOT NULL on `is_potential_violation`, FK on `monitoring_record_id`, performance indexes, and RLS policies.
- **Action:** No complementary migration file was needed.

### TAREA 1.1 & 1.2: Workers already implemented
- **Status at start:** The recovery and destruction workers were already properly implemented with VAEService integration, upsert semantics (`ON CONFLICT`), and no hardcoded values. The task description referenced stubs with values like `45.7` and `0.23` — these had already been replaced prior to this implementation session.
- **Action:** No rewrite needed. Workers verified as correctly using `VAEService.analyze_recovery()` and `VAEService.detect_land_use_change()` with proper signatures.

### TAREA 1.5: `anomaly_type` column reference
- **Status at start:** The monitoring.py endpoint already uses `activity_type` and `human_activity_detected` columns (not `anomaly_type`). The column rename had already been applied.
- **Action:** No change needed for column references.

### TAREA 1.6: INTERVAL parameterization
- **Status at start:** The query already uses the correct form: `INTERVAL '1 month' * :min_months`.
- **Action:** No change needed.

### TAREA 1.7: Cloud cover fallback
- **Status at start:** `vae_service.py:_get_current_ndvi()` already implements the escalating fallback pattern with `cloud_thresholds = [30, 50, 70]` and `window_days = [30, 60, 90]`.
- **Action:** No change needed.

### TAREA 1.8: GET recovery endpoint already reads from DB
- **Status at start:** The endpoint reads from `vegetation_monitoring` table (no GEE calls). Returns `pending` status when no data exists.
- **Action:** No change needed.

### TAREA 2.1: JWT auth already applied
- **Status at start:** `app/main.py` already includes `dependencies=[Depends(get_current_user)]` on the monitoring router.
- **Action:** No change needed.

### TAREA 2.2: Error messages already sanitized
- **Status at start:** All `HTTPException` responses in monitoring.py use generic Spanish messages (e.g., "Servicio de análisis temporalmente no disponible"). No `str(e)` in HTTP details.
- **Action:** No change needed.

### TAREA 2.3: POST trigger already complete
- **Status at start:** The trigger endpoint has admin check (`current_user.is_admin`), rate limiting via `make_generation_rate_limiter()`, `queue='vae'`, and returns 202.
- **Action:** No change needed.

### TAREA 3.2: NdviChart already aligned
- **Status at start:** The NdviChart component already accepts `{ month: string, value: number, recovery_percentage, cloud_cover_pct }` which aligns with how RecoveryPanel maps the API data.
- **Action:** No change needed. The component uses `month` (which is actually a date string) and `value` (ndvi_mean).

### TAREA 3.4: Violation markers already implemented
- **Status at start:** `FireMarkers.tsx` already supports `is_potential_violation` with a differentiated red marker icon (warning triangle). `FireMapItem` type in `map.ts` already includes `is_potential_violation?: boolean`.
- **Action:** Only wired `is_potential_violation` through `MapPage.tsx` episode mapping and added to `EpisodeListItem` type.

### TAREA 3.5: RecoveryPanel already had basic skeleton
- **Status at start:** RecoveryPanel had a basic 3-line skeleton. Enhanced with:
  - Structured skeleton matching the actual layout (header + metric cards + chart + land use cards)
  - Dedicated empty state component for `pending` status with plant icon and descriptive text.

### TAREA 3.3: RecoveryStatusBadge in fire-card
- **Note:** The `recovery_status` field on `EpisodeListItem` is optional and currently not returned by the episodes API endpoint. The badge will render conditionally only when the field is present. A future API enhancement to include `recovery_status` in the episodes response will activate this without frontend changes.

### TAREA 4.1: Batch functions redesigned
- **Deviation:** The original `batch_recovery_analysis` accepted only `fire_event_ids` as a required param. Redesigned to accept optional IDs — when None/empty, the function self-queries the DB for active events within 36 months. This makes it compatible with Celery Beat scheduling without external orchestration.

---

## Items Already Correct (Pre-existing)

| Task | Status | Notes |
|------|--------|-------|
| 0.1 Migration exists | OK | All constraints present |
| 1.1 Recovery worker | OK | Uses VAEService, no hardcoded values |
| 1.2 Destruction worker | OK | Uses VAEService, upsert semantics |
| 1.5 anomaly_type | OK | Already uses activity_type |
| 1.6 INTERVAL | OK | Correct parameterization |
| 1.7 Cloud fallback | OK | Escalating thresholds implemented |
| 1.8 DB-only GET | OK | No GEE calls in endpoint |
| 2.1 JWT auth | OK | Depends(get_current_user) on router |
| 2.2 Error sanitization | OK | Generic messages in all HTTPExceptions |
| 2.3 Trigger endpoint | OK | Admin + rate limit + vae queue + 202 |
| 3.2 NdviChart | OK | Compatible with API format |
| 3.4 Violation markers | OK | Icon + type already present |

---

## Changes Applied

| File | Change | Phase |
|------|--------|-------|
| `workers/celery_app.py` | Routes recovery/destruction to `vae` queue; added beat schedule entries | 1, 2 |
| `celery_app.py` (root) | Updated docstring; added `batch_destruction_detection` route | 1 |
| `docker-compose.yml` | Added `worker-vae` service | 1 |
| `app/api/routes/monitoring.py` | Updated `_classify_status` to frontend-compatible taxonomy; updated `status_counts` keys | 1, 3 |
| `app/main.py` | Updated monitoring OpenAPI tag description | 4 |
| `app/services/vae_service.py` | Documented recovery_percentage formula | 4 |
| `workers/tasks/recovery.py` | Redesigned `batch_recovery_analysis` with self-query | 4 |
| `workers/tasks/destruction.py` | Added `batch_destruction_detection` with self-query | 4 |
| `frontend/src/types/episode.ts` | Added `recovery_status` and `is_potential_violation` fields | 3 |
| `frontend/src/components/fires/fire-card.tsx` | Added RecoveryStatusBadge import and conditional rendering | 3 |
| `frontend/src/components/monitoring/RecoveryPanel.tsx` | Enhanced skeleton + empty state; extracted LandUseChangeCard | 3 |
| `frontend/src/components/monitoring/LandUseChangeCard.tsx` | New file (extracted from RecoveryPanel) | 3 |
| `frontend/src/pages/MapPage.tsx` | Wired `is_potential_violation` through episode mapping | 3 |
