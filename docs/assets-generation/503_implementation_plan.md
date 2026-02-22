# Fix: Production 503 Errors & Wrong Image URLs

## Background

All 22 tasks are implemented and pushed. After deploying, three categories of failures appear:

1. `POST /api/v1/reports/judicial` → **503 Service Unavailable**
2. `POST /api/v1/explorations/{id}/generate` → **503 Service Unavailable**
3. Carousel thumbnails load from `http://127.0.0.1:9000/…` → **ERR_CONNECTION_REFUSED**

Root cause analysis found **4 distinct bugs**, all related to the storage layer.

---

## Root Cause Summary

| # | Bug | Location | Symptom |
|---|-----|----------|---------|
| BUG-1 | `STORAGE_BACKEND=gcs` but **no GCS credentials** configured in prod | [.env](file:///c:/Users/nicog/wildfire-recovery-argentina/.env) + Docker env | 503 on reports & explorations |
| BUG-2 | **No `oci` backend** in [StorageService](file:///c:/Users/nicog/wildfire-recovery-argentina/app/services/storage_service.py#113-860) — falls through to R2/boto3 which also has no credentials | [app/services/storage_service.py](file:///c:/Users/nicog/wildfire-recovery-argentina/app/services/storage_service.py) | 503 when backend=oci is set |
| BUG-3 | `STORAGE_PUBLIC_URL=http://127.0.0.1:9000` (MinIO dev URL) stored in DB | [.env](file:///c:/Users/nicog/wildfire-recovery-argentina/.env) + `SatelliteImage.thumbnail_url` + `fire_episodes.slides_data` | ERR_CONNECTION_REFUSED in browser |
| BUG-4 | `pdf_generation_task` routes to **`reports` queue**, but **no `worker-reports` container** in [docker-compose.yml](file:///c:/Users/nicog/wildfire-recovery-argentina/docker-compose.yml) | [workers/celery_app.py](file:///c:/Users/nicog/wildfire-recovery-argentina/workers/celery_app.py) + [docker-compose.yml](file:///c:/Users/nicog/wildfire-recovery-argentina/docker-compose.yml) | PDF tasks silently queue but never run |

---

## Proposed Changes

---

### Storage Service — OCI Backend

#### [MODIFY] [storage_service.py](file:///c:/Users/nicog/wildfire-recovery-argentina/app/services/storage_service.py)

OCI Object Storage exposes an **S3-compatible endpoint** (`objectstorage.<region>.oci.customer-oci.com`). The existing boto3 [_get_client()](file:///c:/Users/nicog/wildfire-recovery-argentina/app/services/storage_service.py#181-220) already handles S3-compatible endpoints via R2 — we just need to treat `oci` as a backend alias that reads from OCI-specific env vars.

**Changes:**
- Add `oci` as an accepted backend value — it behaves identically to the existing R2/boto3 code path, reading from `OCI_S3_ACCESS_KEY`, `OCI_S3_SECRET_KEY`, `OCI_S3_ENDPOINT_URL`
- Update the production guardrail on line 154–158 to allow `oci` (currently only blocks [local](file:///c:/Users/nicog/wildfire-recovery-argentina/app/services/storage_service.py#174-176))
- Update [get_public_url()](file:///c:/Users/nicog/wildfire-recovery-argentina/app/services/storage_service.py#518-546) to read `OCI_PUBLIC_URL` when backend is `oci`
- Update [health_check()](file:///c:/Users/nicog/wildfire-recovery-argentina/app/services/ers_service.py#1985-2004) to label the backend as `oci` instead of `r2` when applicable

**New env vars needed on VM:**
```
STORAGE_BACKEND=oci
OCI_S3_ENDPOINT_URL=https://objectstorage.<region>.oci.customer-oci.com    # S3-like endpoint
OCI_S3_ACCESS_KEY=<OCI Customer Secret Key ID>
OCI_S3_SECRET_KEY=<OCI Customer Secret Key>
OCI_PUBLIC_URL=https://objectstorage.<region>.oci.customer-oci.com/n/<namespace>/b/forestguard-images/o
# OR use a CDN/PAR URL if buckets are public
```

> [!IMPORTANT]
> OCI Object Storage supports S3-compatible API. You need to create an **S3 Customer Secret Key** in the OCI Console under Identity → Users → Your User → Customer Secret Keys. This is different from the regular OCI API Key.

---

### Docker Compose — Worker-Reports & Env Alignment

#### [MODIFY] [docker-compose.yml](file:///c:/Users/nicog/wildfire-recovery-argentina/docker-compose.yml)

**Changes:**

1. **Add `worker-reports` service** — needed so tasks on the `reports` queue actually get processed:
```yaml
worker-reports:
  build:
    context: .
    dockerfile: Dockerfile.worker
  container_name: forestguard-worker-reports
  environment:
    # (same vars as worker-analysis)
    STORAGE_BACKEND: ${STORAGE_BACKEND:-oci}
    OCI_S3_ENDPOINT_URL: ${OCI_S3_ENDPOINT_URL}
    OCI_S3_ACCESS_KEY: ${OCI_S3_ACCESS_KEY}
    OCI_S3_SECRET_KEY: ${OCI_S3_SECRET_KEY}
    OCI_PUBLIC_URL: ${OCI_PUBLIC_URL}
    CELERY_BROKER_URL: redis://redis:6379/0
    CELERY_RESULT_BACKEND: redis://redis:6379/1
    ...
  command: celery -A workers.celery_app worker --loglevel=info --queues=reports --concurrency=2
```

2. **Replace `ENVIRONMENT: development` with `ENVIRONMENT: ${ENVIRONMENT:-production}`** in all worker and api services — the current hardcoded `development` prevents the OCI guardrail from ever triggering correctly and could disable production-only checks.

3. **Replace OCI cred env vars** — change from `OCI_CONFIG_FILE: /home/opc/.oci/config` (file-based OCI SDK auth) to the S3-compatible key vars above, which work with boto3 without needing the OCI SDK.

---

### Environment Variables

#### [MODIFY] [.env.template](file:///c:/Users/nicog/wildfire-recovery-argentina/.env.template)

Add/clarify the OCI S3-compatible storage section:

```ini
# =============================================================================
# STORAGE — OCI Object Storage (S3-compatible API)
# =============================================================================
STORAGE_BACKEND=oci
# S3-Compatible endpoint (region-specific, e.g. sa-saopaulo-1)
OCI_S3_ENDPOINT_URL=https://objectstorage.sa-saopaulo-1.oci.customer-oci.com
OCI_S3_ACCESS_KEY=<Customer Secret Key ID from OCI Console>
OCI_S3_SECRET_KEY=<Customer Secret Key from OCI Console>
# Public base URL (used to build object URLs returned to frontend)
# Use PAR URL or CDN if buckets are public-read; otherwise omit and use signed URLs
OCI_PUBLIC_URL=

# Bucket names (must exist in OCI)
STORAGE_BUCKET_IMAGES=forestguard-images
STORAGE_BUCKET_REPORTS=forestguard-reports
STORAGE_BUCKET_CERTIFICATES=forestguard-certificates

# Legacy (not used when STORAGE_BACKEND=oci — can be removed)
# STORAGE_PUBLIC_URL=http://127.0.0.1:9000  ← this causes ERR_CONNECTION_REFUSED
```

---

### Database — Repair Stale 127.0.0.1:9000 URLs

> [!WARNING]
> The `STORAGE_PUBLIC_URL=http://127.0.0.1:9000` was stored in the database when the carousel task ran with the local MinIO config. These URLs must be corrected or the carousel will always fail in prod.

#### [NEW] [scripts/fix_stale_minio_urls.sql](file:///c:/Users/nicog/wildfire-recovery-argentina/scripts/fix_stale_minio_urls.sql)

SQL script to null-out stale MinIO URLs so the carousel task regenerates them on next run:

```sql
-- Step 1: Null out thumbnail_url in satellite_images where URL is local
UPDATE satellite_images
   SET thumbnail_url = NULL,
       r2_url = NULL
 WHERE thumbnail_url LIKE 'http://127.0.0.1%'
    OR thumbnail_url LIKE 'http://localhost%';

-- Step 2: Clear slides_data in fire_episodes that reference local URLs
-- (carousel task will regenerate on next daily run or manual refresh)
UPDATE fire_episodes
   SET slides_data = '[]'::jsonb
 WHERE slides_data::text LIKE '%127.0.0.1%'
    OR slides_data::text LIKE '%localhost%';

-- Verify
SELECT COUNT(*) AS stale_satellite_images
  FROM satellite_images
 WHERE thumbnail_url LIKE 'http://127.0.0.1%';

SELECT COUNT(*) AS stale_episodes
  FROM fire_episodes
 WHERE slides_data::text LIKE '%127.0.0.1%';
```

---

## Execution Order on VM

Once the code is pushed, run this sequence on the production VM:

```bash
# 1. Set the new OCI env vars in .env (or export them in shell)
# 2. Apply the SQL patch
psql "$DATABASE_URL" -f scripts/fix_stale_minio_urls.sql

# 3. Rebuild and restart all containers
docker compose pull
docker compose build --no-cache api worker-analysis worker-reports
docker compose up -d

# 4. Trigger a manual carousel refresh to regenerate thumbnails
docker compose exec api python -c "
from app.db.session import SessionLocal
from app.services.imagery_service import ImageryService
db = SessionLocal()
svc = ImageryService(db)
result = svc.run_carousel(max_fires=20, force_refresh=True)
print(result)
db.close()
"
```

---

## Verification Plan

### Automated Tests

```bash
# Run existing unit tests
python -m pytest tests/unit/test_reports_auth.py -v

# Run storage service unit tests (if present)
python -m pytest tests/ -k "storage" -v
```

### Manual Verification (on VM)

**1. Check storage connectivity:**
```bash
docker compose exec api python -c "
from app.services.storage_service import StorageService
s = StorageService()
print(s.health_check())
"
# Expected: {"status": "healthy", "backend": "oci", ...}
```

**2. Test report generation:**
```bash
# Get an auth token first, then:
curl -s -X POST https://forestguard.freedynamicdns.org/api/v1/reports/judicial \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"fire_event_id": "<valid-uuid>"}' | jq .
# Expected: 200 with pdf_url field, NOT 503
```

**3. Test explorations generate:**
```bash
curl -s -X POST https://forestguard.freedynamicdns.org/api/v1/explorations/<ID>/generate \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Idempotency-Key: $(uuidgen)" | jq .
# Expected: 202 Accepted, NOT 503
```

**4. Verify thumbnail URLs in DB:**
```sql
SELECT thumbnail_url FROM satellite_images LIMIT 5;
-- Expected: OCI URLs (not 127.0.0.1)
```

**5. Check worker-reports is running:**
```bash
docker compose ps
# Expected: forestguard-worker-reports Up
```

**6. Verify browser:**
- Open the home page and confirm fire cards show satellite images (not broken images)
- Open DevTools → Network → confirm image URLs are OCI URLs, not 127.0.0.1
