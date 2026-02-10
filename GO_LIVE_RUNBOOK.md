# ForestGuard Go-Live Runbook

## Purpose

This runbook provides step-by-step instructions for validating ForestGuard's readiness for production deployment. Follow these steps to ensure all critical systems are operational before going live.

---

## Prerequisites

### Required
- Backend API running on `http://localhost:8000`
- PostgreSQL database accessible (Supabase)
- `.env` file configured with all required variables

### Optional (for full validation)
- Redis running on `localhost:6379` (for Celery workers)
- Google Cloud Storage credentials configured (for GCS tests)
- Frontend running on `http://localhost:5173` (for UI validation)

---

## Quick Start

### Automated Smoke Test

Run the automated smoke test script:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/go_live_smoke.ps1
```

**Expected output**: All critical tests pass (exit code 0)

---

## Manual Validation Steps

### 1. Start the Backend

```powershell
# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Start the API
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Verify the API is running:
```powershell
curl http://localhost:8000/health
```

Expected: `{"status":"healthy","version":"3.0.0","environment":"development"}`

---

### 2. Health Checks

Test all health endpoints:

```powershell
# Root health
curl http://localhost:8000/health

# Database
curl http://localhost:8000/api/v1/health/db

# Celery (Redis)
curl http://localhost:8000/api/v1/health/celery

# Google Earth Engine
curl http://localhost:8000/api/v1/health/gee
```

**Go criteria**: All return HTTP 200 with `"status": "healthy"` or `"status": "degraded"` (degraded is acceptable for optional services)

---

### 3. Feature Flags Validation

Verify that UC-F07 (refugios/shelters) and UC-F10 (certificates) are blocked:

```powershell
# Certificates endpoint should return 404
curl -i http://localhost:8000/api/v1/certificates/verify/test
# Expected: HTTP 404 with {"detail":"Not available in MVP"}

# Visitor logs endpoint should return 404
curl -i http://localhost:8000/api/v1/visitor-logs
# Expected: HTTP 404

# Shelters endpoint should return 404
curl -i http://localhost:8000/api/v1/shelters
# Expected: HTTP 404
```

**Frontend validation** (requires frontend running):
1. Navigate to `http://localhost:5173/certificates` → should see 404 page
2. Navigate to `http://localhost:5173/shelters` → should see 404 page
3. Check navbar → "Certificates" and "Shelters" links should NOT be visible

---

### 4. GCS Connectivity (Optional)

**Prerequisites**: 
- `GOOGLE_APPLICATION_CREDENTIALS` set in `.env` OR
- Application Default Credentials configured (`gcloud auth application-default login`)

Run the GCS connectivity test:

```powershell
python scripts/test_gcs_conn.py
```

**Go criteria**: All 3 buckets pass (images, reports, certificates)

**Output location**: `artifacts/gcs_conn_report.json`

**If test fails**:
- Check `GCS_PROJECT_ID` in `.env`
- Verify service account has "Storage Object Admin" role
- Ensure buckets exist in GCS console

---

### 5. Celery Workers (Optional)

**Prerequisites**: Redis running on `localhost:6379`

Start a Celery worker:

```powershell
celery -A celery_app worker --loglevel=info --pool=solo
```

Test with a debug task:

```python
from celery_app import debug_task
result = debug_task.delay()
print(result.get(timeout=10))
```

**Go criteria**: Task completes without errors

---

### 6. MVP Use Cases Validation

#### UC-F03: Fire History Dashboard

```powershell
# List fires (requires authentication)
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/api/v1/fires/

# Fire stats
curl http://localhost:8000/api/v1/fires/stats
```

#### UC-F04: Data Quality

```powershell
# Quality metrics for a fire event
curl http://localhost:8000/api/v1/quality/fire-event/FIRE_EVENT_ID
```

#### UC-F06: Land Use Audit

```powershell
# Audit endpoint (requires API key)
curl -X POST \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"lat":-34.0,"lon":-64.0,"radius_km":5}' \
  http://localhost:8000/api/v1/audit/land-use
```

---

## Go / No-Go Decision

### Critical Criteria (MUST PASS)

- ✅ All 4 health endpoints return 200
- ✅ Feature flags block certificates and shelters (404)
- ✅ UC-F03, UC-F04, UC-F06 endpoints respond correctly

### Optional Criteria (WARNINGS OK)

- ⚠️ GCS connectivity (can be configured in production)
- ⚠️ Celery workers (can be started separately)

---

## Post-MVP: Enabling Feature Flags

To enable certificates or shelters after MVP:

### Backend

Edit `.env`:
```env
FEATURE_CERTIFICATES=true
FEATURE_REFUGES=true
```

Restart the API.

### Frontend

Edit `frontend/.env`:
```env
VITE_FEATURE_CERTIFICATES=true
VITE_FEATURE_REFUGES=true
```

Rebuild and restart the frontend:
```powershell
cd frontend
npm run build
npm run preview
```

---

## Troubleshooting

### Health check fails for database
- Verify `DB_HOST`, `DB_USER`, `DB_PASSWORD` in `.env`
- Test connection: `psql -h HOST -U USER -d DATABASE`

### Health check fails for Celery
- Verify Redis is running: `redis-cli ping` (should return `PONG`)
- Check `REDIS_URL` in `.env`

### GCS test fails with 403 Forbidden
- Service account needs "Storage Object Admin" role
- Grant via GCS console → IAM & Admin → Add role

### GCS test fails with 404 Not Found
- Buckets don't exist
- Create in GCS console with names from `.env`:
  - `STORAGE_BUCKET_IMAGES`
  - `STORAGE_BUCKET_REPORTS`
  - `STORAGE_BUCKET_CERTIFICATES`

---

## Contact

For issues or questions, contact the ForestGuard team.
