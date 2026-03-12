# Data Workflow: `GET /api/v1/audit/reverse-geocode`

## 1. Frontend → API Request

**File:** `frontend/src/services/endpoints/geocode.ts` → `reverseGeocode(lat, lon)`

```
apiClient.get('/audit/reverse-geocode', { params: { lat, lon } })
```

Same `apiClient` interceptor attaches `Authorization` and `X-API-Key` headers.

**Called from:** Fire detail page (map interaction)

---

## 2. Nginx → API Proxy

Same as fires/stats — `location ^~ /api/` forwards all headers.

---

## 3. API Route + Authentication

**File:** `app/api/v1/audit.py`

### Router-Level Auth (L55)

```python
router = APIRouter(dependencies=[Depends(get_current_user)])
```

**ALL audit endpoints** require JWT auth — this applies to:
- `POST /audit/land-use`
- `GET /audit/geocode`
- `GET /audit/reverse-geocode`
- `GET /audit/search`

### Auth Chain: `auth_deps.get_current_user()` (L18-93)

```
1. HTTPBearer(auto_error=False) → credentials or None
2. Flow:
   ├─ No credentials → 401 "No se proporciono token de autenticacion"
   └─ credentials present:
       └─ decode_supabase_token(token):
           ├─ _get_expected_issuer() → settings.SUPABASE_URL + "/auth/v1"
           │   └─ If SUPABASE_URL not set → AuthError("Supabase URL no configurado")
           ├─ _get_jwks() → fetch from SUPABASE_URL + "/.well-known/jwks.json"
           │   └─ If URL unreachable → AuthError("No se pudo obtener JWKS")
           └─ jwt.decode(token, public_key, issuer=expected_issuer)
               ├─ Success → get_or_create_supabase_user(db, payload) → User
               └─ Failure → AuthError various messages
```

### Key Dependencies:
- `SUPABASE_URL` — must be in container env
- `SUPABASE_JWT_AUDIENCE` — defaults to "authenticated"
- Network access to Supabase JWKS endpoint

---

## 4. Endpoint Handler

**File:** `app/api/v1/audit.py` L352-368

```python
@router.get("/reverse-geocode")
def reverse_geocode_location(lat, lon):
    result = GeocodingService().reverse_geocode(lat, lon)
```

### Service: `GeocodingService.reverse_geocode()`
- Makes HTTP request to Nominatim reverse geocoding API
- URL: `https://nominatim.openstreetmap.org/reverse`
- Returns: `GeocodeResponse(query, result)`

---

## 5. Error Analysis

| Symptom | Code | Root Cause |
|---------|------|------------|
| 401 "No se proporciono token" | auth_deps.py L46 | Bearer token not in request headers |
| 401 "Supabase URL no configurado" | supabase_auth.py L71 | `SUPABASE_URL` missing from container env |
| 401 "Token invalido" | supabase_auth.py L165 | JWT decode failure (expired, wrong issuer) |
| 401 "No se pudo obtener JWKS" | supabase_auth.py L106 | Container can't reach Supabase JWKS URL |

