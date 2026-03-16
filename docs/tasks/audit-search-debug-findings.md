# Diagnóstico: búsqueda textual /audit — request no visible en Network

## 1. Bloque try/catch y condiciones en Audit.tsx

### handleSubmit (líneas 250–292)

**Flujo:**
1. `auditMutation.reset()`, `setLocalError(null)`, `setCurrentPage(1)`.
2. **Guard de autenticación:** `if (status !== 'authenticated')` → `setLocalError(t('authRequired'))` y **return**. Si el usuario no está autenticado, **no se llama a searchAuditEpisodes** y no hay request.
3. **Rama búsqueda textual:** `const query = values.search?.trim()`; `if (query)`:
   - `setSearchLoading(true)`, `setSearchResult(null)`, `setLastSearchQuery(query)`, `setLastSearchRadiusKm(...)`.
   - **try:** `await searchAuditEpisodes(query, { limit: 20, radius_km: ... })` → `setSearchResult(response)`.
   - **catch:** solo `setLocalError(t('geocodeNotFound'))`. **No se hace console.error ni se re-lanza el error.** Cualquier fallo (red, 401, 404, 500, URL incorrecta) se traduce en el mismo mensaje genérico y el error real queda oculto.
   - **finally:** `setSearchLoading(false)`.
   - **return** (no se evalúa lat/lon).
4. Si no hay `query`, se evalúa búsqueda por punto (`values.lat && values.lon`) o `setLocalError(t('noPointError'))`.

**Conclusión:** El catch suprime el error por completo. Para ver por qué falla la llamada hay que añadir logging (p. ej. `console.error`) en el catch.

### Botón Submit (líneas 594–597)

- `disabled={auditMutation.isPending || searchLoading || !form.formState.isValid}`.
- Si `form.formState.isValid` es false (p. ej. `radius_m` fuera de rango o inválido), el usuario no puede enviar el formulario y **nunca se dispara handleSubmit**, por tanto tampoco searchAuditEpisodes.

### Restauración desde FireDetail (useEffect líneas 168–212)

- Cuando `restore.origin === 'search'` se llama `searchAuditEpisodes(restore.q, { limit: 20, radius_km: restore.radius_km })` con `.then(...).catch(() => setLocalError(t('geocodeNotFound'))).finally(...)`.
- El **catch** tampoco registra el error; mismo problema que en handleSubmit.

---

## 2. apiClient y interceptores (api.ts)

- **URL base:** `API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '/api/v1').replace(/\/$/, '')`. Si no hay `VITE_API_BASE_URL`, se usa `/api/v1` (ruta relativa al origen del frontend). La llamada a search es `apiClient.get('/audit/search', { params: { q, limit, radius_km } })`, URL final: `{baseURL}/audit/search`.
- **Request interceptor** (`requestInterceptor`): Añade `X-API-Key` (si `API_KEY`), `Authorization: Bearer <token>` (si `getAuthToken()` devuelve token), y `Content-Type: application/json` si no está definido. No rechaza ni cancela la petición; solo prepara headers. En DEV hace `console.log('🔍 Axios Request Interceptor:', ...)` y `console.log('✅ Request prepared:', ...)`.
- **Response error interceptor** (`responseErrorInterceptor`): En 401 con JWT hace un intento de refresh y reenvío; si falla, llama a `handleHttpError` (toast "Session expired" + redirect a /login). Luego `Promise.reject(error)` — el error llega al llamador. Para 403/422/429/5xx/red hace toast y rechaza. En DEV ya hay `console.error('🚨 Axios Response Error Interceptor:', ...)` con message, code, status, url, method, responseData.
- **Conclusión:** Los interceptores no bloquean la petición. Si no aparece el request en Network, las causas probables son: (1) guard `status !== 'authenticated'`, (2) formulario inválido (botón disabled), (3) sin `query`, o (4) excepción síncrona antes de que axios envíe. Añadir `console.error` en los catch del frontend expone el error real cuando la promesa de searchAuditEpisodes falla.

---

## 3. Causa raíz y corrección mínima

- **Causa raíz del síntoma “no se ven requests”:** Si el usuario ve la grilla con "N/D" en ID de incendio pero no ve requests, o bien (A) nunca se está llamando a `searchAuditEpisodes` (guardas o formulario inválido), o bien (B) la llamada se hace, falla (p. ej. 401/403/500/red), el catch la oculta y la UI muestra estado anterior o `geocodeNotFound` sin pista del fallo.
- **Corrección mínima aplicada (sin cambiar lógica de negocio):** Se añadió en ambos sitios que llaman a searchAuditEpisodes un `console.error` en el catch: (1) `handleSubmit`: `catch (error) { console.error('searchAuditEpisodes failed', error); setLocalError(...) }`; (2) Restore desde FireDetail: `.catch((error) => { console.error('restore searchAuditEpisodes failed', error); setLocalError(...) })`. Así en la consola del navegador se ve el error real cuando la promesa falla. Se mantiene el comportamiento de `setLocalError(t('geocodeNotFound'))` y de la UI.

---

## 4. Verificación manual (Network y Console)

- **Tests automatizados:** Los tests en `frontend/src/pages/__tests__/AuditPage.test.tsx` pasan (4/4) con los cambios.
- **Verificación en navegador (dev):** (1) Usuario no autenticado: en `/audit`, buscar por texto y enviar → debe mostrarse "authRequired" y no debe aparecer request a `/audit/search` en Network. (2) Usuario autenticado: buscar p. ej. "Chubut" con radio 1 km → en Network debe aparecer `GET .../audit/search?q=Chubut&limit=20&radius_km=1`; si falla, en Console aparece `searchAuditEpisodes failed` con el error. (3) Restore desde FireDetail: si la re-llamada al volver falla, en Console aparece `restore searchAuditEpisodes failed`.
