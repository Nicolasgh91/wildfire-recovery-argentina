# Notas de testing

## 2026-02-03 - Reportes /verify devolvia 404 aunque existia audit_events

### Sintoma
- `GET /api/v1/reports/{report_id}/verify` respondia 404 ("Report not found").
- El registro existia en `audit_events` y era visible con un SELECT directo.
- Los tests `tests/integration/test_reports_verify.py` fallaban con 404.

### Causa raiz
- El endpoint primero consulta `generated_reports`.
- En entornos donde la tabla no existe, ese SELECT lanza excepcion y deja la transaccion en estado "aborted".
- Al no hacer `rollback()`, la consulta posterior a `audit_events` falla silenciosamente, resultando en 404.

### Correccion
- Agregar `db.rollback()` en los `except` alrededor de los SELECTs en `verify_report`.
- Esto permite que la query a `audit_events` se ejecute correctamente.

### Leccion para tests futuros
- Si un endpoint ejecuta multiples SELECTs y alguno puede fallar por tablas no presentes, hacer rollback antes de continuar.
- En tests de integracion, cuando se fuerza un flujo "fallback", validar que las transacciones se limpien entre queries.

## 2026-02-03 - E2E /fires no veia datos insertados en tests

### Sintoma
- `tests/e2e/test_critical_flows.py::test_dashboard_flow_e2e` fallaba porque la respuesta de `/api/v1/fires/` estaba vacia.
- En los logs se veia un 307 al pedir `/api/v1/fires` (sin slash) y luego 200 con lista vacia.

### Causa raiz
- `user_client` overrideaba solo `app.db.session.get_db`, pero `/api/v1/fires` usa `app.api.deps.get_db`.
- El endpoint consultaba otra base (DATABASE_URL), no la de tests (TEST_DATABASE_URL), por eso no veia los inserts del test.

### Correccion
- Agregar override tambien para `app.api.deps.get_db` en `tests/conftest.py`.
- Ajustar el test a `/api/v1/fires/` para evitar 307 y limpiar datos creados.

### Leccion para tests futuros
- Si un endpoint usa `deps.get_db`, el override debe cubrir ambas dependencias (session.get_db y deps.get_db).
- Verificar que la URL del endpoint coincida con el trailing slash para evitar redirects en E2E.

## 2026-02-04 - Test FireDetail falla por Embla/Carousel en JSDOM

### Sintoma
- `src/__tests__/fire-detail.test.tsx` fallaba con `TypeError: undefined is not a function` dentro de `embla-carousel`.

### Causa raiz
- Embla usa `window.matchMedia` para resolver media queries.
- JSDOM no define `matchMedia` por defecto, y la inicializacion del carrusel falla.

### Correccion
- Mock de `matchMedia` en `frontend/src/test/setup.ts` para el entorno Vitest.

### Leccion para tests futuros
- Cuando se agreguen componentes que dependan de APIs de browser (matchMedia, ResizeObserver, etc.), incluir mocks en el setup global de tests.

### Actualizacion
- Embla tambien usa `IntersectionObserver`, por lo que se agrego mock adicional en el setup global.

## 2026-02-04 - E2E FireDetail (Cypress)

### Nota
- Se agrego un test E2E en `frontend/cypress/e2e/fire-detail.cy.ts`.
- Requiere variables: `CYPRESS_TEST_USER_EMAIL`, `CYPRESS_TEST_USER_PASSWORD`, `CYPRESS_API_KEY`.
- El test obtiene un `fire_id` via `GET /api/v1/fires` con `X-API-Key`, luego navega a `/fires/:id`.

### Nota de timing
- Los tests de integracion que consultan backend real pueden tardar >5s; se aumento el timeout del test FireDetail a 20s.

## 2026-02-04 - FireDetail integration fallaba por falta de endpoint

### Sintoma
- `fire-detail.integration.test.tsx` mostraba "Error al cargar el incendio." al intentar abrir `/fires/:id`.

### Causa raiz
- El backend no tenia implementado el endpoint `GET /api/v1/fires/{id}` requerido por FireDetail.

### Correccion
- Se agrego `GET /api/v1/fires/{id}` en `app/api/v1/fires.py` y `FireService.get_fire_detail` en `app/services/fire_service.py`.

## 2026-02-04 - FireDetail integration 500 por columna faltante en fire_climate_associations

### Sintoma
- `GET /api/v1/fires/{id}` devolvia 500 con `column fire_climate_associations.distance_meters does not exist`.

### Causa raiz
- La tabla `fire_climate_associations` (migracion T0.2) no tiene `distance_meters`.
- Al acceder a `fire.climate_association`, SQLAlchemy intentaba cargar columnas inexistentes.

### Correccion
- Alinear el modelo `FireClimateAssociation` con la tabla real (id UUID, `association_type`, `hours_offset`, `distance_km`, `relevance_weight`, `created_at`).
- Cambiar la relacion en `FireEvent` a `climate_associations` (N:M) para evitar que SQLAlchemy intente cargar columnas inexistentes.
- Mantener el calculo de `has_climate_data` via query simple en `FireService.get_fire_detail`.
