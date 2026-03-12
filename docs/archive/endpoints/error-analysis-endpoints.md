# Endpoint Errors: Root Cause Analysis & Fixes

**Date:** 2026-02-23  
**Affected endpoints:** `/fires/stats` (500), `/audit/reverse-geocode` (401)

## Summary of Errors Found

| # | Endpoint | HTTP | Error Detail | Root Cause | Fix |
|---|----------|------|-------------|------------|-----|
| E-1 | `/fires/stats` | 500 | Internal Server Error | `API_KEY` now reaches container but `_get_secret_value()` may fail, or `get_stats()` DB query crashes | Check API logs for traceback |
| E-2 | `/audit/reverse-geocode` | 401 | "No se proporciono token" | JWT token not parsed OR `SUPABASE_URL` not in container env | Add `SUPABASE_URL` to docker-compose.yml (done) + verify frontend sends Bearer token |
| E-3 | ALL API-key endpoints | 403 | "Missing/Invalid API Key" | `API_KEY` was missing from `docker-compose.yml` api service env | Added `API_KEY: ${API_KEY}` to docker-compose.yml (done) |
| E-4 | ALL JWT endpoints | 401 | Various | `SUPABASE_URL`, `SUPABASE_JWT_SECRET` were missing from api container env | Added to docker-compose.yml (done) |

---

## E-1: `/fires/stats` → 500 Internal Server Error

### Data Flow
```
Frontend getFireStats() 
  → apiClient.get('/fires/stats') with X-API-Key + Bearer headers
  → nginx proxy_pass http://api:8000
  → fires.py: require_fire_access() (JWT or API key auth)
  → fire_service.py: get_stats() (6 DB queries)
  → Response: StatsResponse JSON
```

### Probable Cause
The error changed from 403 → 500 after adding `API_KEY` to docker-compose.yml. This means:
1. Auth now passes (API_KEY matches) ✅
2. But `get_stats()` crashes during execution ❌

**Most likely:** The `API_KEY` value in `.env` has surrounding **quotes** that cause `_get_secret_value()` to strip them, but `secrets.compare_digest()` still fails because the frontend sends the quoted version. OR, a DB query in `get_stats()` fails due to missing table/column.

### Diagnostic
```bash
docker compose logs --tail=50 api 2>&1 | grep -A5 "fires/stats\|500\|Error\|Traceback"
```

---

## E-2: `/audit/reverse-geocode` → 401 Unauthorized

### Data Flow
```
Frontend reverseGeocode(lat, lon)
  → apiClient.get('/audit/reverse-geocode', {params: {lat, lon}}) with Bearer header
  → nginx proxy_pass http://api:8000
  → audit.py: router-level Depends(get_current_user)
  → auth_deps.py: parse Bearer token from Authorization header
  → supabase_auth.py: decode_supabase_token()
    → _get_expected_issuer(): requires SUPABASE_URL
    → _get_jwks(): fetches from SUPABASE_URL + "/.well-known/jwks.json"
    → jwt.decode(): validates token signature, issuer, audience
  → GeocodingService.reverse_geocode(lat, lon)
  → GeocodeResponse
```

### Probable Cause
Two scenarios:
1. **`SUPABASE_URL` not in container env** → `_get_expected_issuer()` raises `AuthError("Supabase URL no configurado")` → 401
2. **Frontend doesn't send Bearer token** → `credentials` is None → "No se proporciono token"

### Diagnostic
```bash
docker compose exec api env | grep SUPABASE_URL
docker compose logs --tail=50 api 2>&1 | grep -A5 "reverse-geocode\|Auth\|401"
```

---

## Fixes Already Applied

| File | Change |
|------|--------|
| `docker-compose.yml` | Added `API_KEY`, `ADMIN_API_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `SUPABASE_JWT_SECRET` to api service env |
| `app/main.py` | Removed JWT requirement from monitoring router (public GET endpoints) |
| `app/api/v1/quality.py` | Removed API key requirement from quality GET endpoint |
| `.github/workflows/post-deploy-storage.yml` | Fixed `set -e` silent failures (BUG-8) |

## Remaining Diagnostic Steps

1. **Get the 500 traceback** from api container logs  
2. **Verify env vars loaded** in the deployed container  
3. **Check frontend token** — is the `Authorization: Bearer` header sent?

