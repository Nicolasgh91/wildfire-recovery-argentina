# Data Workflow: `GET /api/v1/fires/stats`

## 1. Frontend → API Request

**File:** `frontend/src/services/endpoints/fires.ts` → `getFireStats()`

```
apiClient.get('/fires/stats', { params: filters })
```

The `apiClient` (Axios) interceptor in `frontend/src/services/api.ts:requestInterceptor` attaches:
- `X-API-Key: <VITE_API_KEY || SUPABASE_ANON_KEY>` (L80-82)
- `Authorization: Bearer <Supabase JWT from localStorage>` (L84-87)

**Called from:** `FireHistory-DcwXgtKr.js` (React Query `queryFn`)

---

## 2. Nginx → API Proxy

**File:** `nginx.conf` L193-214

```
location ^~ /api/ {
    proxy_pass $api_upstream;   # http://api:8000
}
```

Forwards all headers including `Authorization` and `X-API-Key`.

---

## 3. API Route + Authentication

**File:** `app/api/v1/fires.py` L226-231

```python
@router.get("/stats", dependencies=[Depends(require_fire_access)])
```

### Auth Chain: `require_fire_access()` (L100-117)

```
1. HTTPBearer(auto_error=False)  → credentials (JWT) or None
2. APIKeyHeader(auto_error=False) → api_key (X-API-Key header) or None
3. Flow:
   ├─ credentials present → _resolve_jwt_user() → decode_supabase_token()
   │   ├─ Success → return User
   │   └─ Fail → fallback to api_key if present
   ├─ api_key present → verify_api_key_user() → security.get_current_user()
   │   ├─ Compares with settings.API_KEY (SecretStr)
   │   └─ Compares with settings.ADMIN_API_KEY (SecretStr)
   └─ Neither → HTTPException(401, "Authentication required")
```

### API Key Validation: `app/core/security.py` L63-92

```python
settings.API_KEY   → SecretStr from env → _get_secret_value() strips quotes
settings.ADMIN_API_KEY → same
```

**CRITICAL:** `API_KEY` must be in docker-compose.yml env → container env → `settings.API_KEY`.

---

## 4. Service Layer: `FireService.get_stats()`

**File:** `app/services/fire_service.py` L1168-1333

```
1. build_filter_conditions(params) → SQLAlchemy filters
2. _summary_query(filters) → COUNT, SUM, AVG on fire_events
3. percentile_cont(0.5) → median hectares
4. GROUP BY province → by_province stats
5. GROUP BY date_trunc('month') → by_month trends
6. JOIN fire_protected_area_intersection → fires_in_protected count
7. ORDER BY max_frp DESC → top_frp_fires (top 10)
8. _kpi_snapshot() → YTD comparison with previous year
```

### Tables Queried:
- `fire_events` (main)
- `fire_protected_area_intersection` (JOIN)

### Response Schema: `StatsResponse`
- `stats.total_fires`, `stats.active_fires`, `stats.by_province[]`, `stats.by_month{}`
- `ytd_comparison` with delta percentages

---

## 5. Error Analysis

| Symptom | Code | Root Cause |
|---------|------|------------|
| 403 "Missing API Key" | security.py L76 | `API_KEY` not in container env |
| 403 "Invalid API Key" | security.py L92 | Key mismatch (quotes, wrong value) |
| 500 Internal Server Error | fires.py/fire_service.py | Runtime error in auth or DB query |
| 401 "Authentication required" | fires.py L117 | No JWT and no API key provided |
