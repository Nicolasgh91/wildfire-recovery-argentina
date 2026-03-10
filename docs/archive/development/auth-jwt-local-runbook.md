# Auth JWT local validation (Supabase ES256)

## Requisitos
- Backend corriendo en `http://localhost:8000`
- Token Supabase disponible en el navegador (localStorage `sb-<project>-auth-token`)

## Obtener token
1. Abrir DevTools > Application > Local Storage.
2. Buscar `sb-<project>-auth-token`.
3. Copiar `access_token` y exportarlo:
   - PowerShell: `$env:TOKEN = "<access_token>"`

## Ejecutar request con curl (sin loguear token)
```powershell
$env:API_KEY = (Select-String -Path .env -Pattern '^API_KEY=').Line.Split('=')[1].Trim('"')
$headers = @{ Authorization = "Bearer $env:TOKEN"; "x-api-key" = $env:API_KEY }
Invoke-WebRequest -Uri "http://localhost:8000/api/v1/audit/search?q=chubut&limit=20&radius_km=1" -Headers $headers -Method GET -Verbose 2> temp_files\\curl_auth.log 1> temp_files\\curl_auth.out
```

Si querés usar `curl`, en PowerShell hay que llamar a `curl.exe` para evitar el alias:
```powershell
curl.exe -H "Authorization: Bearer $env:TOKEN" -H "x-api-key: $env:API_KEY" "http://localhost:8000/api/v1/audit/search?q=chubut&limit=20&radius_km=1" -v 2> temp_files\\curl_auth.log 1> temp_files\\curl_auth.out
```

Si recibís `{"detail":"Invalid API Key"}`, probá sin `x-api-key` (en estos endpoints el JWT es suficiente):
```powershell
$headers = @{ Authorization = "Bearer $env:TOKEN" }
Invoke-WebRequest -Uri "http://localhost:8000/api/v1/audit/search?q=chubut&limit=20&radius_km=1" -Headers $headers -Method GET -Verbose 2> temp_files\\curl_auth.log 1> temp_files\\curl_auth.out
```

## Qué mirar en logs
- `Auth check` con `authorization_present=true` y `bearer_parsed=true`
- `JWT validate` con `alg=ES256` y `expected_issuer=https://<project>.supabase.co/auth/v1`
- Cualquier `JWT decode failed` con detalle y stacktrace acotado

## Tests relevantes
- `pytest tests/integration/test_auth_supabase_jwt.py`

## Pruebas finales (manuales)
- Audit (JWT ok): `200 OK`
```powershell
$headers = @{ Authorization = "Bearer $env:TOKEN"; "x-api-key" = $env:API_KEY }
Invoke-WebRequest -UseBasicParsing -Uri "http://localhost:8000/api/v1/audit/search?q=chubut&limit=20&radius_km=1" -Headers $headers -Method GET -Verbose
```
- Explorations (crear y listar): `201 Created` + `200 OK`
```powershell
$fire = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/fire-events/search?q=chubut&page_size=1" -Method GET
$fireId = $fire.fires[0].id
$body = @{ fire_event_id = $fireId; title = "Test exploracion" } | ConvertTo-Json
Invoke-WebRequest -UseBasicParsing -Uri "http://localhost:8000/api/v1/explorations/" -Headers $headers -Method POST -Body $body -ContentType "application/json" -Verbose
Invoke-WebRequest -UseBasicParsing -Uri "http://localhost:8000/api/v1/explorations/" -Headers $headers -Method GET -Verbose
```
- Payments (balance + checkout): `200 OK`
```powershell
Invoke-WebRequest -UseBasicParsing -Uri "http://localhost:8000/api/v1/payments/credits/balance" -Headers $headers -Method GET -Verbose
$checkoutBody = @{ purpose = "credits"; credits_amount = 5; client_platform = "web" } | ConvertTo-Json
Invoke-WebRequest -UseBasicParsing -Uri "http://localhost:8000/api/v1/payments/checkout" -Headers $headers -Method POST -Body $checkoutBody -ContentType "application/json" -Verbose
```

## Gotchas
- Usar `access_token` de `sb-<project>-auth-token`. No usar `refresh_token` ni `provider_token`.
- Token expirado devuelve `{"detail":"Token expirado"}`.
- En PowerShell, `curl` es alias de `Invoke-WebRequest`. Usar `curl.exe` si querés salida tipo curl.
- Para `/api/v1/explorations/` usar **slash final**. Sin slash, FastAPI responde 307 y PowerShell puede perder `Authorization`.
- Si falta tabla `user_investigations` o `payment_requests`, aplicar migraciones:
  - `database/migrations/014_create_exploration_investigations.sql`
  - `database/migrations/015_exploration_investigations_rls.sql`
  - `database/migrations/016_add_hd_generation_job_idempotency.sql`
  - `database/migrations/2026_02_04_payment_tables.sql`

## Checklist final (auth + explorations + payments)
- [x] JWT Supabase ES256 validado con JWKS (aud/iss correctos).
- [x] `/api/v1/audit/search` responde `200 OK` con `Authorization: Bearer <access_token>`.
- [x] `/api/v1/explorations/` responde `201` (create) y `200` (list).
- [x] `/api/v1/payments/credits/balance` responde `200 OK`.
- [x] `/api/v1/payments/checkout` responde `200 OK` (mock mode).

