# Ruc home/landing execution log

> Documento archivado. El comportamiento vigente de rutas está normalizado en `docs/frontend/routing_access_ruc.md` y `docs/frontend/README.md`. Usar este archivo solo como log histórico de ejecución.

## Scope
- **Goal**: Implement approved routing plan (no commits) for:
  - Root gate in `/`:
    - guest -> `/login`
    - authenticated -> `/home`
  - Home moved to `/home`
  - Publish RUC table in docs and validate with tests.
- **Restriction applied**: No commits were created.

## TSK-01 - Documento RUC en docs
### A) Planificacion minima
- **Archivos afectados**:
  - `docs/frontend/routing_access_ruc.md`
  - `docs/INDEX.md`
  - `docs/frontend/README.md`
- **Riesgo identificado**: Desalineacion entre reglas documentadas y rutas reales.
- **DoD**: Matriz RUC-01..RUC-14 publicada y enlazada.

### B) Implementacion
- Added `docs/frontend/routing_access_ruc.md` with RUC-01..RUC-14.
- Updated `docs/INDEX.md` to include RUC document.
- Updated `docs/frontend/README.md` routing section and API contract notes for `/` and `/home`.

### C-D) Validacion
- Cross-checked route behavior against `frontend/src/App.tsx` after implementation.
- Result: Passed.

### E) Deuda tecnica
- No ambiguity found in rules definition.

## TSK-02 - Ruteo raiz condicional + Home en `/home`
### A) Planificacion minima
- **Archivos afectados**:
  - `frontend/src/App.tsx`
  - `frontend/src/components/auth/ProtectedRoute.tsx`
  - `frontend/src/lib/routing.ts` (new shared route resolver)
- **Riesgo identificado**: Incorrect transition in `loading` state for root gate.
- **DoD**: `/` enforza RUC-01 behavior.

### B) Implementacion
- Added `resolveRootDestination()` and constants in `frontend/src/lib/routing.ts`.
- Replaced `/` route element with `RootRouteGate` in `frontend/src/App.tsx`.
- Added explicit `/home` route for `HomePage`.
- Updated `ProtectedRoute` role fallback from `/` to `/home`.
- Hid navbar/footer at `/` to reduce redirect flicker.

### C-D) Validacion
- Validated by tests on root resolver logic and by route inspection.
- Result: Passed.

### E) Deuda tecnica
- No blocker. Potential UX flicker mitigated by hiding chrome at `/`.

## TSK-03 - Migracion de referencias Home a `/home`
### A) Planificacion minima
- **Archivos afectados**:
  - `frontend/src/components/layout/navbar.tsx`
  - `frontend/src/pages/FireDetail.tsx`
  - `frontend/src/pages/PaymentReturnPage.tsx`
  - `frontend/src/pages/CitizenReport.tsx`
  - `frontend/src/pages/NotFound.tsx`
  - `frontend/src/pages/AuthCallback.tsx`
  - `frontend/src/pages/Login.tsx`
  - `frontend/src/pages/Register.tsx`
- **Riesgo identificado**: Legacy links to `/` leaving inconsistent behavior.
- **DoD**: Home/inicio actions resolve to `/home`; login remains canonical in `/login`.

### B) Implementacion
- Migrated home links and `navigate('/')` calls to `/home`.
- Kept landing canonical route in `/login`.
- Added `resolveReturnToPath()` and migrated auth fallback defaults to `/home`.

### C-D) Validacion
- Searched for remaining `navigate('/')` and `|| '/'` fallbacks in `frontend/src`.
- Result: No remaining matches.

### E) Deuda tecnica
- No residual references found in scoped files.

## TSK-04 - Suite de tests frontend
### A) Planificacion minima
- **Archivos afectados**:
  - `frontend/src/test/setup.ts` (new)
  - `frontend/src/lib/routing.test.ts` (new)
- **Riesgo identificado**: Frontend tests previously failed due no test files.
- **DoD**: Tests created and passing.

### B) Implementacion
- Added Vitest setup file with Testing Library cleanup and jest-dom matchers.
- Added unit tests for:
  - `resolveRootDestination`:
    - authenticated -> `/home`
    - unauthenticated -> `/login`
    - loading -> `null`
    - unexpected states fallback -> `/login`
  - `resolveReturnToPath`:
    - valid path kept
    - null/undefined fallback to `/home`
    - empty/whitespace fallback to `/home`
    - custom fallback support

### C-D) Validacion obligatoria
- Command: `npm test -- --run` (in `frontend`)
  - Result: **PASS**
  - Metrics: `1` test file, `8` tests passed.
- Command: `npm run build` (in `frontend`)
  - Result: **PASS**
  - Metrics: build success, `3459` modules transformed, build time ~`20.65s`.
  - Notes: Non-blocking warnings about chunk size and dynamic import splitting.

### E) Deuda tecnica
- Logged in `docs/frontend/technical_debt.md`:
  - TD-FE-001 (oversized chunk warning)
  - TD-FE-002 (dynamic import/static import overlap)

## TSK-05 - Cierre y entregables
### Estado
- [x] Tabla RUC publicada en docs.
- [x] Ruteo implementado segun RUC-01.
- [x] Tests de ruta y edge cases agregados.
- [x] Suite validada (`test` + `build`).
- [x] Log de ejecucion completo.
- [x] Sin commits.

## Comandos ejecutados
1. `git status --short`
2. `npm test -- --run` (frontend)
3. `npm run build` (frontend)
4. `rg`/`Get-Content` checks for route references and docs consistency

## Issues abiertos
- See `docs/frontend/technical_debt.md`
