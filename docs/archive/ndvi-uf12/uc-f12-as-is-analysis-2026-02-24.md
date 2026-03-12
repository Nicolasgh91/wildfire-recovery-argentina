> **Nota de vigencia (2026-03)**  
> Este documento describe el estado **AS-IS** previo al refactor de cuotas GEE y a la estructuración de flujos CORE.  
> Para la vista canónica actual de UC‑F12/NDVI usar:
> - `docs/core-flows/core-vae-ucf12-ndvi/core-vae-overview.md`  
> - `docs/core-flows/core-vae-ucf12-ndvi/core-vae-design.md`  
> Este archivo se conserva como análisis histórico y mapa de gaps, no como fuente de verdad vigente.

# UC-F12 VAE AS-IS Analysis (2026-02-24)

## 1) Scope

This report documents the current ("as-is") flow for UC-F12 / UC-06 (VAE: recovery + land-use change), including:

- Data generation, processing, persistence, and API exposure.
- What is currently rendered in UI and on which pages.
- Naming conflict map between `UC-12` and `UC-F12`.
- Gap analysis between documentation and current code.

This is analysis-only. No runtime or production DB state validation was executed.

## 2) Nomenclature Map (UC-12 vs UC-F12)

| Label in code/docs | Current meaning in repo | Evidence |
|---|---|---|
| `UC-F12` | Recovery + land-use change VAE flow | `app/api/routes/monitoring.py`, `docs/archive/ndvi-uf12/*` |
| `UC-06` | Vegetation recovery monitoring (same technical area as VAE monitoring) | `app/main.py` tag metadata and monitoring router comments |
| `UC-12` | Visitor logs / shelters | `app/main.py` tag `visitor-logs`, `app/api/routes/visitor_logs.py` |
| `UC-12` (also used) | Historical reports context | `app/api/routes/historical.py`, `app/services/ers_service.py`, `app/services/vae_service.py` |

### Key conflict

`UC-12` is overloaded in multiple domains (visitor logs and historical reports), while VAE uses `UC-F12` and `UC-06`. This creates documentation and communication drift.

## 3) AS-IS Backend Flow

### 3.1 API surface today (`/api/v1/monitoring`)

Endpoints implemented in router:

- `GET /monitoring/recovery/summary`
- `GET /monitoring/recovery/{fire_event_id}`
- `GET /monitoring/land-use-changes/{fire_event_id}`
- `POST /monitoring/recovery/trigger`

Evidence:

- `@router.get` decorators in [app/api/routes/monitoring.py](c:/Users/nicog/wildfire-recovery-argentina/app/api/routes/monitoring.py:209), [app/api/routes/monitoring.py](c:/Users/nicog/wildfire-recovery-argentina/app/api/routes/monitoring.py:333), [app/api/routes/monitoring.py](c:/Users/nicog/wildfire-recovery-argentina/app/api/routes/monitoring.py:499)
- `@router.post` decorator in [app/api/routes/monitoring.py](c:/Users/nicog/wildfire-recovery-argentina/app/api/routes/monitoring.py:588)

### 3.2 Auth behavior in runtime

- Monitoring router is mounted **without** router-level JWT dependency.
- Explicit comment says GET endpoints are public; only trigger uses auth dependency.
- Trigger endpoint uses `current_user: User = Depends(get_current_user)` and admin check.

Evidence:

- Public GET design note and include_router call in [app/main.py](c:/Users/nicog/wildfire-recovery-argentina/app/main.py:235), [app/main.py](c:/Users/nicog/wildfire-recovery-argentina/app/main.py:236), [app/main.py](c:/Users/nicog/wildfire-recovery-argentina/app/main.py:238)
- Trigger auth dependency in [app/api/routes/monitoring.py](c:/Users/nicog/wildfire-recovery-argentina/app/api/routes/monitoring.py:610)

### 3.3 Data generation and enqueue path

Manual trigger path:

1. `POST /monitoring/recovery/trigger` (admin only, rate-limited).
2. Enqueues:
   - `workers.tasks.recovery.analyze_recovery`
   - `workers.tasks.destruction.detect_destruction`
3. Both are enqueued explicitly with `queue="vae"`.

Evidence:

- Trigger section in [app/api/routes/monitoring.py](c:/Users/nicog/wildfire-recovery-argentina/app/api/routes/monitoring.py:588), [app/api/routes/monitoring.py](c:/Users/nicog/wildfire-recovery-argentina/app/api/routes/monitoring.py:636), [app/api/routes/monitoring.py](c:/Users/nicog/wildfire-recovery-argentina/app/api/routes/monitoring.py:640)

### 3.4 Processing and persistence path

Recovery worker:

- Gets fire geometry from `fire_events`.
- Calls `VAEService.analyze_recovery(...)`.
- Persists into `vegetation_monitoring` using `INSERT ... ON CONFLICT (fire_event_id, monitoring_date)`.

Evidence:

- Task declaration and queue in [workers/tasks/recovery.py](c:/Users/nicog/wildfire-recovery-argentina/workers/tasks/recovery.py:16), [workers/tasks/recovery.py](c:/Users/nicog/wildfire-recovery-argentina/workers/tasks/recovery.py:19)
- VAE call in [workers/tasks/recovery.py](c:/Users/nicog/wildfire-recovery-argentina/workers/tasks/recovery.py:83)
- Upsert in [workers/tasks/recovery.py](c:/Users/nicog/wildfire-recovery-argentina/workers/tasks/recovery.py:129)

Destruction worker:

- Gets fire geometry from `fire_events`.
- Calls `VAEService.detect_land_use_change(...)`.
- Persists into `land_use_changes` with `ON CONFLICT (fire_event_id, change_detected_at)`.

Evidence:

- Task declaration and queue in [workers/tasks/destruction.py](c:/Users/nicog/wildfire-recovery-argentina/workers/tasks/destruction.py:16), [workers/tasks/destruction.py](c:/Users/nicog/wildfire-recovery-argentina/workers/tasks/destruction.py:19)
- VAE call in [workers/tasks/destruction.py](c:/Users/nicog/wildfire-recovery-argentina/workers/tasks/destruction.py:76)
- Upsert in [workers/tasks/destruction.py](c:/Users/nicog/wildfire-recovery-argentina/workers/tasks/destruction.py:120)

### 3.5 Read path and response behavior

Recovery read:

- Reads `fire_events` + `vegetation_monitoring`.
- If no rows, returns `200` with `recovery_status="pending"` and empty data.
- If rows exist, maps latest row into aggregate status via `_classify_status(...)`.

Evidence:

- Status classifier in [app/api/routes/monitoring.py](c:/Users/nicog/wildfire-recovery-argentina/app/api/routes/monitoring.py:185)
- Pending response in [app/api/routes/monitoring.py](c:/Users/nicog/wildfire-recovery-argentina/app/api/routes/monitoring.py:438)

Land-use read:

- Reads `land_use_changes` by `fire_event_id`.
- Returns array + `violation_count`.

Evidence:

- Query + response assembly in [app/api/routes/monitoring.py](c:/Users/nicog/wildfire-recovery-argentina/app/api/routes/monitoring.py:499)

### 3.6 Queue routing and consumption reality

Important runtime mismatch:

- Worker task definitions and trigger enqueue use `vae`.
- Runtime Celery routes map these tasks to `analysis`.
- Docker compose starts workers for `ingestion`, `clustering`, `analysis`, `reports` only. No worker for `vae`.

Evidence:

- Routes in [workers/celery_app.py](c:/Users/nicog/wildfire-recovery-argentina/workers/celery_app.py:96), [workers/celery_app.py](c:/Users/nicog/wildfire-recovery-argentina/workers/celery_app.py:105), [workers/celery_app.py](c:/Users/nicog/wildfire-recovery-argentina/workers/celery_app.py:106)
- Worker queues in [docker-compose.yml](c:/Users/nicog/wildfire-recovery-argentina/docker-compose.yml:148), [docker-compose.yml](c:/Users/nicog/wildfire-recovery-argentina/docker-compose.yml:203), [docker-compose.yml](c:/Users/nicog/wildfire-recovery-argentina/docker-compose.yml:258), [docker-compose.yml](c:/Users/nicog/wildfire-recovery-argentina/docker-compose.yml:317)
- Explicit `queue="vae"` from trigger in [app/api/routes/monitoring.py](c:/Users/nicog/wildfire-recovery-argentina/app/api/routes/monitoring.py:636), [app/api/routes/monitoring.py](c:/Users/nicog/wildfire-recovery-argentina/app/api/routes/monitoring.py:640)

Additional drift:

- There is another top-level `celery_app.py` that routes to `vae`, but workers are started with `workers.celery_app` in compose.

Evidence:

- Top-level alternate routes in [celery_app.py](c:/Users/nicog/wildfire-recovery-argentina/celery_app.py:71)
- Runtime worker command in [docker-compose.yml](c:/Users/nicog/wildfire-recovery-argentina/docker-compose.yml:258)

### 3.7 Persistence hardening migration (present in repo)

Migration file defines:

- Unique constraints for both monitoring tables.
- `NOT NULL` for `is_potential_violation`.
- FK `land_use_changes.monitoring_record_id -> vegetation_monitoring.id`.
- RLS enable + read/write policies.

Evidence:

- Migration file [database/migrations/2026_02_23_uc_f12_vae_monitoring.sql](c:/Users/nicog/wildfire-recovery-argentina/database/migrations/2026_02_23_uc_f12_vae_monitoring.sql:19), [database/migrations/2026_02_23_uc_f12_vae_monitoring.sql](c:/Users/nicog/wildfire-recovery-argentina/database/migrations/2026_02_23_uc_f12_vae_monitoring.sql:24), [database/migrations/2026_02_23_uc_f12_vae_monitoring.sql](c:/Users/nicog/wildfire-recovery-argentina/database/migrations/2026_02_23_uc_f12_vae_monitoring.sql:44), [database/migrations/2026_02_23_uc_f12_vae_monitoring.sql](c:/Users/nicog/wildfire-recovery-argentina/database/migrations/2026_02_23_uc_f12_vae_monitoring.sql:66), [database/migrations/2026_02_23_uc_f12_vae_monitoring.sql](c:/Users/nicog/wildfire-recovery-argentina/database/migrations/2026_02_23_uc_f12_vae_monitoring.sql:70), [database/migrations/2026_02_23_uc_f12_vae_monitoring.sql](c:/Users/nicog/wildfire-recovery-argentina/database/migrations/2026_02_23_uc_f12_vae_monitoring.sql:78)

Note: file presence is confirmed; application in target DB is not verified here.

## 4) AS-IS Frontend Flow

### 4.1 Where VAE is rendered today

Main rendering page:

- Public route `/fires/:id` exists.
- `RecoveryPanel` renders only when:
  - user is authenticated
  - detail is not an episode-only detail (`!isEpisodeDetail`)

Evidence:

- Route in [frontend/src/App.tsx](c:/Users/nicog/wildfire-recovery-argentina/frontend/src/App.tsx:146)
- Gate in [frontend/src/pages/FireDetail.tsx](c:/Users/nicog/wildfire-recovery-argentina/frontend/src/pages/FireDetail.tsx:413), [frontend/src/pages/FireDetail.tsx](c:/Users/nicog/wildfire-recovery-argentina/frontend/src/pages/FireDetail.tsx:415)

`RecoveryPanel` behavior:

- Calls `useRecovery(fireEventId)` and `useLandUseChanges(fireEventId)`.
- Renders:
  - status badge
  - baseline/current/recovery metric cards
  - NDVI chart
  - land-use cards (only if `changes.length > 0`)

Evidence:

- Hook calls in [frontend/src/components/monitoring/RecoveryPanel.tsx](c:/Users/nicog/wildfire-recovery-argentina/frontend/src/components/monitoring/RecoveryPanel.tsx:52), [frontend/src/components/monitoring/RecoveryPanel.tsx](c:/Users/nicog/wildfire-recovery-argentina/frontend/src/components/monitoring/RecoveryPanel.tsx:53)
- Main UI blocks in [frontend/src/components/monitoring/RecoveryPanel.tsx](c:/Users/nicog/wildfire-recovery-argentina/frontend/src/components/monitoring/RecoveryPanel.tsx:88), [frontend/src/components/monitoring/RecoveryPanel.tsx](c:/Users/nicog/wildfire-recovery-argentina/frontend/src/components/monitoring/RecoveryPanel.tsx:91), [frontend/src/components/monitoring/RecoveryPanel.tsx](c:/Users/nicog/wildfire-recovery-argentina/frontend/src/components/monitoring/RecoveryPanel.tsx:118), [frontend/src/components/monitoring/RecoveryPanel.tsx](c:/Users/nicog/wildfire-recovery-argentina/frontend/src/components/monitoring/RecoveryPanel.tsx:128)

### 4.2 Frontend API contracts used

Client endpoint contracts:

- `GET /monitoring/recovery/{fireEventId}`
- `GET /monitoring/land-use-changes/{fireEventId}`

Evidence:

- Endpoint client in [frontend/src/services/endpoints/monitoring.ts](c:/Users/nicog/wildfire-recovery-argentina/frontend/src/services/endpoints/monitoring.ts:45), [frontend/src/services/endpoints/monitoring.ts](c:/Users/nicog/wildfire-recovery-argentina/frontend/src/services/endpoints/monitoring.ts:56), [frontend/src/services/endpoints/monitoring.ts](c:/Users/nicog/wildfire-recovery-argentina/frontend/src/services/endpoints/monitoring.ts:50), [frontend/src/services/endpoints/monitoring.ts](c:/Users/nicog/wildfire-recovery-argentina/frontend/src/services/endpoints/monitoring.ts:61)
- Query keys in [frontend/src/lib/queryClient.ts](c:/Users/nicog/wildfire-recovery-argentina/frontend/src/lib/queryClient.ts:28)
- Hooks in [frontend/src/hooks/queries/useRecovery.ts](c:/Users/nicog/wildfire-recovery-argentina/frontend/src/hooks/queries/useRecovery.ts:5), [frontend/src/hooks/queries/useLandUseChanges.ts](c:/Users/nicog/wildfire-recovery-argentina/frontend/src/hooks/queries/useLandUseChanges.ts:5)

Auth transport note:

- Central API client adds JWT `Authorization` header if token exists.

Evidence:

- Interceptor in [frontend/src/services/api.ts](c:/Users/nicog/wildfire-recovery-argentina/frontend/src/services/api.ts:84), [frontend/src/services/api.ts](c:/Users/nicog/wildfire-recovery-argentina/frontend/src/services/api.ts:86)

### 4.3 Pages where VAE is not shown (today)

Home feed (`/`) uses `components/fires/fire-card` (episode card) and does not consume monitoring endpoints.

Evidence:

- Import/usage in [frontend/src/pages/Home.tsx](c:/Users/nicog/wildfire-recovery-argentina/frontend/src/pages/Home.tsx:8), [frontend/src/pages/Home.tsx](c:/Users/nicog/wildfire-recovery-argentina/frontend/src/pages/Home.tsx:13), [frontend/src/pages/Home.tsx](c:/Users/nicog/wildfire-recovery-argentina/frontend/src/pages/Home.tsx:216)

Map page (`/map`) does not call monitoring endpoints. It builds map items from episode data only.

Evidence:

- Map item builder in [frontend/src/pages/MapPage.tsx](c:/Users/nicog/wildfire-recovery-argentina/frontend/src/pages/MapPage.tsx:63)

### 4.4 Marker-level violation capability vs data feed

- Marker component supports `is_potential_violation` visual differentiation.
- `MapPage` map item object does not set `is_potential_violation`.
- Result: capability exists in marker layer, but not fed by current map data flow.

Evidence:

- Marker icon function in [frontend/src/components/map/layers/FireMarkers.tsx](c:/Users/nicog/wildfire-recovery-argentina/frontend/src/components/map/layers/FireMarkers.tsx:27), [frontend/src/components/map/layers/FireMarkers.tsx](c:/Users/nicog/wildfire-recovery-argentina/frontend/src/components/map/layers/FireMarkers.tsx:93)
- Map item shape in [frontend/src/types/map.ts](c:/Users/nicog/wildfire-recovery-argentina/frontend/src/types/map.ts:18)
- Map item creation missing that field in [frontend/src/pages/MapPage.tsx](c:/Users/nicog/wildfire-recovery-argentina/frontend/src/pages/MapPage.tsx:77)

## 5) Current API/Type Contract Observations

### 5.1 Backend recovery status taxonomy

`_classify_status` returns:

- `suspicious`, `unknown`, `excellent`, `good`, `moderate`, `poor`, `critical`
- plus `pending` for no-data branch

Evidence:

- Classifier in [app/api/routes/monitoring.py](c:/Users/nicog/wildfire-recovery-argentina/app/api/routes/monitoring.py:185)
- Pending branch in [app/api/routes/monitoring.py](c:/Users/nicog/wildfire-recovery-argentina/app/api/routes/monitoring.py:438)

### 5.2 Frontend badge taxonomy

`RecoveryStatusBadge` supports:

- `not_started`, `early_recovery`, `moderate_recovery`, `advanced_recovery`, `full_recovery`, `stalled`, `anomaly_detected`, `pending`

Unknown status values fallback to `not_started`.

Evidence:

- Union + config + fallback in [frontend/src/components/monitoring/RecoveryStatusBadge.tsx](c:/Users/nicog/wildfire-recovery-argentina/frontend/src/components/monitoring/RecoveryStatusBadge.tsx:4), [frontend/src/components/monitoring/RecoveryStatusBadge.tsx](c:/Users/nicog/wildfire-recovery-argentina/frontend/src/components/monitoring/RecoveryStatusBadge.tsx:19), [frontend/src/components/monitoring/RecoveryStatusBadge.tsx](c:/Users/nicog/wildfire-recovery-argentina/frontend/src/components/monitoring/RecoveryStatusBadge.tsx:33)

## 6) Gap Analysis (Docs vs Code)

### G1 - Queue routing/consumption mismatch (HIGH)

- Trigger and tasks target `vae`.
- Runtime routes and running workers are `analysis` (no `vae` consumer).
- This can leave trigger-generated jobs unconsumed.

### G2 - Auth expectation mismatch (HIGH)

- Implementation spec says monitoring endpoints should require JWT.
- Runtime intentionally leaves GET monitoring endpoints public.

Evidence:

- Auth requirement in spec [docs/archive/ndvi-uf12/uc-f12-implementation-spec.md](c:/Users/nicog/wildfire-recovery-argentina/docs/archive/ndvi-uf12/uc-f12-implementation-spec.md:93)
- Runtime public GET comment in [app/main.py](c:/Users/nicog/wildfire-recovery-argentina/app/main.py:236)

### G3 - Recovery status contract mismatch (HIGH)

- Backend emits `excellent/good/moderate/poor/critical/suspicious/unknown/pending`.
- Badge expects VAE-style enums (`early_recovery`, etc.).
- Non-matching values fallback to `not_started` label.

### G4 - "Badge in feed" documented vs real active component usage (MEDIUM)

- Documentation expects recovery badge in feed card.
- Active home feed uses `components/fires/fire-card`.
- `components/fire-card.tsx` (with recovery badge) is not used in current route flow.

Evidence:

- Doc expectation in [docs/archive/ndvi-uf12/uc-f12-implementation-spec.md](c:/Users/nicog/wildfire-recovery-argentina/docs/archive/ndvi-uf12/uc-f12-implementation-spec.md:72)
- Active home card usage in [frontend/src/pages/Home.tsx](c:/Users/nicog/wildfire-recovery-argentina/frontend/src/pages/Home.tsx:13)

### G5 - Map violation visualization documented, but data feed missing (MEDIUM)

- Marker layer supports violation icon.
- `MapPage` does not inject `is_potential_violation`.

### G6 - Product docs are stale vs current VAE UI surface (MEDIUM)

- Product docs still mark UC-F12 as "in progress / not exposed as mature product flow".
- Current code already exposes monitoring endpoints and renders `RecoveryPanel` in fire detail under auth gate.

Evidence:

- Product docs in [docs/product/casos-de-uso-y-estado.md](c:/Users/nicog/wildfire-recovery-argentina/docs/product/casos-de-uso-y-estado.md:35), [docs/product/estado-real-del-producto.md](c:/Users/nicog/wildfire-recovery-argentina/docs/product/estado-real-del-producto.md:28)

### G7 - Duplicate Celery configuration sources (MEDIUM)

- Root `celery_app.py` and runtime `workers/celery_app.py` diverge in VAE routing assumptions.
- This increases operational ambiguity and can mislead docs/runbooks.

## 7) Risks

1. Queue risk: manual trigger may report "queued" while queue has no active consumers (`vae`).
2. UX risk: status badge can mislabel healthy recovery as "Sin monitoreo" due enum mismatch.
3. Security/product risk: public GET monitoring may conflict with expected private analysis semantics.
4. Observability risk: split Celery configs make incidents harder to reason about.

## 8) Matrix: Page -> Data -> Endpoint -> Auth -> UI Output

| Page/Route | Data source | Endpoint calls | Auth gate in UI | What user sees |
|---|---|---|---|---|
| `/fires/:id` | Fire detail + monitoring | `/fires/{id}` + `/monitoring/recovery/{id}` + `/monitoring/land-use-changes/{id}` | Recovery panel only if authenticated and not episode detail | Recovery badge, NDVI metrics/cards/chart, land-use cards when changes exist |
| `/` (Home) | Episode list/cards | `/fire-episodes/*` | No VAE section | Feed cards without recovery panel flow |
| `/map` | Episode map items | `/fire-episodes/*` | No VAE fetch | Map markers by severity/status; violation icon capability exists but not currently fed |
| `/fires/history` | Fire list/stats/history | `/fires`, `/fires/stats`, etc. | Protected route | No VAE panel integration in this page |

## 9) Matrix: Endpoint -> Table(s) -> Worker(s) -> Notes

| Endpoint | Read/Write table(s) | Worker producers/consumers | Notes |
|---|---|---|---|
| `GET /monitoring/recovery/{id}` | `fire_events`, `vegetation_monitoring` (read) | Reads worker outputs | Returns `pending` when no rows |
| `GET /monitoring/land-use-changes/{id}` | `fire_events`, `land_use_changes` (read) | Reads worker outputs | Returns `violation_count` |
| `GET /monitoring/recovery/summary` | `fire_events` + latest `vegetation_monitoring` row | Reads worker outputs | Aggregate summary endpoint; no frontend consumer found |
| `POST /monitoring/recovery/trigger` | No direct DB write (enqueue only) | Enqueues `analyze_recovery` + `detect_destruction` | Enqueues to `queue="vae"` explicitly |
| `workers.tasks.recovery.analyze_recovery` | `vegetation_monitoring` (upsert) | Defined as `queue='vae'` but runtime route maps to `analysis` | Potential routing conflict with explicit `vae` enqueue |
| `workers.tasks.destruction.detect_destruction` | `land_use_changes` (upsert) | Defined as `queue='vae'` but runtime route maps to `analysis` | Same queue conflict pattern |

## 10) Validation Scenarios (as requested)

1. Event without monitoring rows:
   - Backend: returns `200` + `recovery_status="pending"` + empty `monitoring_data`.
   - UI: recovery panel can show pending state when authenticated and non-episode detail.
2. Event with NDVI series:
   - Backend returns list in `monitoring_data`.
   - UI renders NDVI chart + metric cards.
3. Event with `land_use_changes` and violations:
   - Backend returns `violation_count`.
   - UI renders change cards and violation badge count.
4. Unauthenticated user in `/fires/:id`:
   - Fire detail page is public.
   - Recovery panel is not rendered (`isAuthenticated` guard).
5. Admin trigger flow:
   - Endpoint validates admin and enqueues jobs.
   - Operational risk remains if `vae` queue has no worker consumer.
6. Main map violation signal:
   - Marker component supports violation flag.
   - Current map feed does not populate that flag, so violation icon is effectively inactive.

## 11) Documentation Drift Snapshot

The implementation spec and product state docs still contain obsolete assumptions in this repo snapshot, e.g.:

- "Frontend recovery tab does not exist" vs `RecoveryPanel` already integrated.
- "Queue vae absent" vs mixed state: some files assume `vae`, runtime compose does not consume it.
- "Monitoring auth mandatory" vs runtime intentionally public GET monitoring endpoints.

## 12) Assumptions

1. Analysis based on repository snapshot at local workspace date 2026-02-24.
2. No live environment checks (DB applied migrations, queue depths, running worker telemetry).
3. No code changes proposed in this report, only factual AS-IS and identified gaps.

