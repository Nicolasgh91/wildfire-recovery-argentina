# Menu + Perfil v2 - Implementacion Full Stack

## 1) Objetivo, alcance y fecha de corte

- Objetivo: documentar de punta a punta los cambios implementados en navegacion responsive (desktop/tablet/mobile), perfil v2, flujo de acceso restringido, eliminacion de cuenta, alineacion de base de datos y guardrails de CI/build.
- Alcance: frontend + backend + database + CI/CD vinculados a este frente.
- Fuera de alcance: nuevos features no implementados en este branch, cambios de arquitectura no presentes en codigo.
- Fecha de corte documental: 2026-02-22.

## 2) Resumen ejecutivo de cambios

- Navegacion centralizada en configuracion tipada (`navigation.ts`) con reglas de visibilidad por auth, estado activo (`activeMatch`) y previews bloqueados para guest (`guestPreview='locked'`).
- UX responsive hibrida:
  - Mobile `<md`: bottom nav (4 slots) + drawer.
  - Tablet `md-<lg`: topbar con hamburguesa + drawer.
  - Desktop `>=lg`: navbar superior tradicional.
- Menu hamburguesa reorganizado: bloques principales + colapsables `Soporte`, `Mas informacion`, `Fuentes publicas`, con `Cuenta` antes de `Preferencias`.
- Matriz de accesos ajustada por contexto:
  - Mobile `Soporte`: FAQ, Manual, Glosario, Contacto.
  - Mobile `Mas informacion`: API docs, Parques Nacionales, Reporte diario.
  - Desktop `Soporte`: FAQ, Manual, Glosario.
  - Desktop `Informativos`: API docs, Parques Nacionales, Reporte diario, Contacto.
  - Desktop `Producto`: incluye Historicos + Verificar terreno segun auth.
- Candados en nav para guest (`Verificar terreno`, `Historicos`) con modal unificado `RestrictedAccessDialog`:
  - `Volver atras`: cierra modal (sin navegar -1 en navbar).
  - `Iniciar sesion`: redirige a `/login` con `state.from`.
- Perfil v2 implementado:
  - Logout reutilizable.
  - Cambio de contrasena con reautenticacion.
  - Reset con mensaje neutro anti-enumeracion + cooldown.
  - UI de eliminacion de cuenta para email/password y OAuth.
- Backend de account lifecycle:
  - `POST /api/v1/account/delete/challenge`.
  - `POST /api/v1/account/delete`.
  - Soft delete + bloqueo de acceso para usuarios eliminados.
  - Revocacion de sesiones via servicio admin.
- DB:
  - `users`: `is_deleted`, `deleted_at`, `deletion_reason`.
  - FK obligatoria de evidencia: `citizen_reports.reporter_user_id -> users(id) ON DELETE SET NULL`.
- CI/build:
  - Workflow frontend forzado a checkout desde `main`.
  - Guardrail de import prohibido de `FirePopupCard`.
  - Hotfix de build aplicado para evitar error de import inexistente.

## 3) Arquitectura de navegacion actual

### Breakpoints y componentes

- Desktop `>=lg`:
  - `frontend/src/components/layout/navbar.tsx`
  - Fuente de datos: `frontend/src/features/navigation/config/navigation.ts`
  - Render con `NavLink` y `end` segun `activeMatch`.
- Tablet `md-<lg`:
  - `frontend/src/features/navigation/components/navigation-topbar-tablet.tsx`
  - Abre `frontend/src/features/navigation/components/navigation-drawer.tsx`.
- Mobile `<md`:
  - `frontend/src/features/navigation/components/navigation-bottom-nav.tsx`
  - Slot menu abre `navigation-drawer.tsx`.

### Source of truth

- Items y reglas: `frontend/src/features/navigation/config/navigation.ts`
  - Tipos: `NavigationItem`, `InternalNavigationItem`, `ExternalNavigationItem`.
  - Match: `activeMatch: 'exact' | 'prefix'`.
  - Candados guest: `guestPreview: 'hidden' | 'locked'`.
  - Helpers: `getVisibleItems`, `getVisibleItemsByIds`, `isLockedPreview`.
- Grupos por contexto: `frontend/src/features/navigation/config/access-groups.ts`.
- Fuentes publicas compartidas: `frontend/src/features/navigation/config/public-sources.ts`.

## 4) Matriz final de accesos Mobile vs Desktop

### Mobile (drawer)

- Soporte:
  - FAQ
  - Manual
  - Glosario
  - Contacto
- Mas informacion:
  - API docs
  - Parques Nacionales
  - Reporte diario de incendios
- Herramientas:
  - Se mantiene sin cambios funcionales.
- Fuentes publicas:
  - Se mantiene sin cambios funcionales.

### Desktop (footer)

- Producto:
  - Inicio
  - Mapa
  - Exploracion satelital
  - Historicos (auth-only)
  - Verificar terreno (auth-only)
- Soporte:
  - FAQ
  - Manual
  - Glosario
- Informativos:
  - API docs
  - Parques Nacionales
  - Reporte diario de incendios
  - Contacto
- Fuentes publicas:
  - Igual dataset que mobile drawer.

### Regla de visibilidad auth

- Guest:
  - En navbar/drawer puede ver previews bloqueados para `audit` y `fires-history` con icono de candado.
  - En footer no se aplican locked previews nuevos.
- Authenticated:
  - `audit` y `fires-history` se comportan como links normales.

## 5) Candados y modal "Acceso restringido"

### Componente compartido

- `frontend/src/components/auth/RestrictedAccessDialog.tsx`
  - Basado en `AlertDialog`.
  - Usa `Z_INDEX.MODAL_CRITICAL`.
  - Microcopy centralizada con `protectedPageTitle`, `protectedPageMessage`, `goBack`, `login`.

### Flujo en navbar/drawer

- Navbar (`frontend/src/components/layout/navbar.tsx`):
  - Click en item locked abre `RestrictedAccessDialog`.
  - `Volver atras`: cierra modal y mantiene pagina actual.
  - `Iniciar sesion`: `navigate('/login', { state: { from: { pathname }, reason: 'nav_locked_item' } })`.
- Drawer (`frontend/src/features/navigation/components/navigation-drawer.tsx`):
  - Propaga `onLockedItemIntent(path)` al navbar.
  - Cierra drawer y delega modal al navbar (single source de UX).

### Nota sobre acceso directo por URL protegida

- `ProtectedRoute` (`frontend/src/components/auth/ProtectedRoute.tsx`) usa tambien `RestrictedAccessDialog`.
- Diferencia clave:
  - En route guard, `onGoBack` sigue usando `navigate(-1)` por compatibilidad de acceso directo.
  - En navbar locked flow, `onGoBack` solo cierra modal.

## 6) Perfil v2 (frontend)

### Hook central de acciones de cuenta

- Archivo: `frontend/src/features/account/hooks/use-account-actions.ts`.
- Funciones:
  - `reauthenticate(currentPassword)`
  - `updatePassword({ newPassword, currentPassword? })`
  - `sendPasswordReset(email?)`
  - `logout()`
  - `requestDeleteChallenge()`
  - `deleteAccount(payload)`
- Comportamiento relevante:
  - Reauth requerida antes de actualizar password en cuentas no OAuth.
  - Reset devuelve mensaje neutro (`RESET_PASSWORD_NEUTRAL_MESSAGE`).

### Componentes

- `password-security-card.tsx`
  - Reauth + update password.
  - Cooldown reset de 30s.
  - UX diferenciada OAuth.
- `logout-action.tsx`
  - Boton reusable en perfil y drawer.
- `delete-account-dialog.tsx`
  - Confirmacion fuerte: texto `ELIMINAR` + password (email/password) o challenge token (OAuth).

### Integracion en pagina de perfil

- `frontend/src/pages/Profile.tsx`
  - Mantiene edicion de datos.
  - Agrega card de seguridad.
  - Agrega acciones de cuenta: logout + delete account.

## 7) Delete account end-to-end (backend + DB + seguridad + auditoria)

### Endpoints

- `POST /api/v1/account/delete/challenge`
  - Router: `app/api/v1/account.py`
  - Emite token temporal para flujo challenge.
  - Respuesta neutra para no filtrar estado de cuenta.
- `POST /api/v1/account/delete`
  - Requiere:
    - `confirmationText == 'ELIMINAR'`
    - Credencial valida: `challengeToken` o `password`.
  - Toma identidad desde JWT (`get_current_user`), no acepta `user_id` explicito.

### Servicios

- `app/services/account_service.py`
  - Emision y verificacion de challenge.
  - Soft delete:
    - `users.is_deleted = true`
    - `users.deleted_at`
    - `users.deletion_reason`
    - anonimiza email/nombre
    - nulifica `citizen_reports.reporter_user_id`
    - registra evento de auditoria
  - Revoca sesiones via servicio admin.
- `app/services/supabase_admin.py`
  - Verificacion de password via Supabase auth.
  - Revocacion global de sesiones (best effort).

### Bloqueo post-delete

- `app/api/auth_deps.py`
  - Si `user.is_deleted == true`, responde `403` (`Cuenta eliminada`).

### Migraciones

- `database/migrations/2026_02_21_users_soft_delete.sql`
  - Agrega columnas soft delete en `users`.
- `database/migrations/2026_02_21_account_delete_fk_alignment.sql`
  - Enforce FK de `citizen_reports.reporter_user_id` con `ON DELETE SET NULL`.
  - Reemplaza constraint previo si no cumple politica.

## 8) Cambios en mapa/build (z-index, overlays, hotfix FirePopupCard)

### z-index y overlays

- Escala central: `frontend/src/features/navigation/config/z-index.ts`.
- Aplicacion:
  - `frontend/src/pages/MapPage.tsx` (overlays map sidebar/carrusel mobile).
  - `frontend/src/components/ui/sheet.tsx` (`z-[400]` overlay, `z-[500]` content, `overscroll-contain`).
  - Dialogs criticos (`RestrictedAccessDialog`, `ExternalConfirmDialog`) con `Z_INDEX.MODAL_CRITICAL`.

### Hotfix de build FirePopupCard

- Causa raiz original: import inexistente `@/components/map/FirePopupCard`.
- Correccion aplicada:
  - `frontend/src/components/map/layers/FireMarkers.tsx` mantiene render inline de popup.
  - Eliminada dependencia al archivo inexistente.
- Guardrail CI:
  - `.github/workflows/frontend-build.yml` bloquea ese import via grep antes de build.

## 9) CI guardrails y politica de build desde `main`

- Workflow: `.github/workflows/frontend-build.yml`.
- Cambios clave:
  - Checkout explicito con `ref: main`.
  - Paso "Print ref and SHA".
  - Paso de guardrail para bloquear import prohibido de `FirePopupCard`.
  - Build multi-arch (`linux/amd64`, `linux/arm64`).
  - Opcion de clean rebuild (`workflow_dispatch` + `clean_rebuild=true`).

## 10) Inventario de archivos modificados/creados (por dominio)

### Tabla A - Archivo/Componente | Cambio implementado | Impacto funcional

| Archivo/Componente | Cambio implementado | Impacto funcional |
|---|---|---|
| `frontend/src/features/navigation/config/navigation.ts` | Modelo tipado de navegacion, `activeMatch`, `guestPreview`, helpers visibilidad | Unifica reglas de nav desktop/mobile/footer y evita drift de links |
| `frontend/src/features/navigation/config/access-groups.ts` | Grupos por contexto mobile/desktop | Matriz de accesos distinta por dispositivo sin duplicar logica |
| `frontend/src/features/navigation/config/public-sources.ts` | Fuente unica de enlaces publicos | Consistencia drawer/footer para fuentes publicas |
| `frontend/src/features/navigation/components/navigation-drawer.tsx` | Estructura final del drawer + hooks de locked intent + externos | Navegacion mobile/tablet consistente y auth-aware |
| `frontend/src/features/navigation/components/navigation-drawer-collapsible-groups.tsx` | Colapsables `Soporte`, `Mas informacion`, `Fuentes publicas` | Cumple taxonomia nueva en mobile/tablet |
| `frontend/src/features/navigation/components/navigation-menu-sections.tsx` | Render de locked previews con candado | Discoverability de rutas auth-only para guests |
| `frontend/src/components/layout/navbar.tsx` | Locked flow con `RestrictedAccessDialog` + drawer/tablet/mobile integration | UX uniforme de acceso restringido |
| `frontend/src/components/layout/footer.tsx` | Footer desktop por grupos explicitos via IDs | Cumple matriz desktop de Soporte/Informativos/Producto |
| `frontend/src/components/auth/RestrictedAccessDialog.tsx` | Modal compartido de acceso restringido | UX consistente entre nav locked y `ProtectedRoute` |
| `frontend/src/components/auth/ProtectedRoute.tsx` | Reuso de dialog compartido | Menor divergencia de copy/comportamiento |
| `frontend/src/features/account/hooks/use-account-actions.ts` | Operaciones de cuenta separadas de `AuthContext` | Mejor separacion de responsabilidades y testeabilidad |
| `frontend/src/features/account/components/password-security-card.tsx` | Reauth + update password + reset neutro/cooldown | Seguridad UX en perfil |
| `frontend/src/features/account/components/logout-action.tsx` | Logout reutilizable | Consistencia perfil/drawer |
| `frontend/src/features/account/components/delete-account-dialog.tsx` | Confirmacion fuerte para delete account | Menor riesgo de acciones destructivas accidentales |
| `frontend/src/pages/Profile.tsx` | Integra perfil v2 | Cuenta gestionable end-to-end desde UI |
| `frontend/src/features/navigation/config/z-index.ts` | Escala de capas centralizada | Evita conflictos con Leaflet/drawers/modales |
| `frontend/src/pages/MapPage.tsx` | Uso de z-index central en overlays | Menos colisiones visuales en mobile/tablet |
| `frontend/src/components/ui/sheet.tsx` | z-index explicito + `overscroll-contain` | Mejor scroll lock/overlay behavior |
| `frontend/src/components/map/layers/FireMarkers.tsx` | Hotfix import popup inexistente | Desbloquea `vite build` |
| `app/api/v1/account.py` | Endpoints challenge/delete de cuenta | API de account lifecycle |
| `app/services/account_service.py` | Lógica de challenge, soft delete y auditoria | Flujo de eliminacion seguro y trazable |
| `app/services/supabase_admin.py` | Verificacion password y revocacion global | Controles server-side para operaciones sensibles |
| `app/api/auth_deps.py` | Bloqueo de `is_deleted` | Usuario eliminado no puede seguir operando |
| `database/migrations/2026_02_21_users_soft_delete.sql` | Campos soft delete en users | Persistencia de baja logica |
| `database/migrations/2026_02_21_account_delete_fk_alignment.sql` | FK `ON DELETE SET NULL` en `citizen_reports` | Preservacion de evidencia con anonimizado de vinculo |
| `.github/workflows/frontend-build.yml` | Checkout en `main` + guardrail import prohibido | Menor riesgo de builds sobre refs erroneos/regresiones |

## 11) Pruebas ejecutadas y resultados observados

### Tabla B - Endpoint/Contrato | Request/Response | Validaciones

| Endpoint/Contrato | Request/Response | Validaciones |
|---|---|---|
| `POST /api/v1/account/delete/challenge` | Request: JWT auth. Response: `{ "message": "Si la cuenta permite este metodo, recibiras un token temporal por email." }` | Respuesta neutra para no exponer estado interno |
| `POST /api/v1/account/delete` | Request body (alias): `confirmationText`, `password?`, `challengeToken?`, `reason?`. Response: `{ "message": "Account deleted" }` | `confirmationText == ELIMINAR`; credencial valida (`password` o `challengeToken`); identidad tomada de JWT |
| Auth dependency (`get_current_user`) | N/A | Si `is_deleted` -> `403 Cuenta eliminada` |

### Tabla C - Pruebas | Cobertura | Estado

| Pruebas | Cobertura | Estado |
|---|---|---|
| `frontend/src/features/navigation/components/__tests__/navigation-drawer-collapsible-groups.test.tsx` | Colapsables mobile (`Soporte`, `Mas informacion`, `Fuentes publicas`) + callbacks externos | OK |
| `frontend/src/features/navigation/components/__tests__/navigation-drawer.test.tsx` | Orden de bloques y locked intent en drawer | OK |
| `frontend/src/components/layout/__tests__/footer-access-groups.test.tsx` | Matriz desktop (Soporte sin Contacto, Informativos con Contacto, Producto auth-aware) | OK |
| `frontend/src/features/navigation/components/__tests__/navigation-menu-sections.test.tsx` | Render y callbacks de locked previews | OK |
| `frontend/src/components/layout/__tests__/navbar-locked-preview.test.tsx` | Modal restringido en navbar + rutas de accion | OK |
| `frontend/src/features/navigation/__tests__/navigation-config.test.ts` | Visibilidad por auth, locked previews, helper por IDs | OK |
| `frontend/src/features/navigation/__tests__/navigation-active-match.test.tsx` | `prefix` vs `exact` en active state | OK |
| `frontend/src/features/navigation/components/__tests__/navigation-error-fallback.test.tsx` | Fallback operativo (`/home`, `/map`, login/logout) | OK |
| `frontend/src/components/auth/__tests__/RestrictedAccessDialog.test.tsx` | Render y callbacks del modal compartido | OK |
| `frontend/src/components/auth/__tests__/ProtectedRoute.test.tsx` | Guard behavior para auth/loading/roles | OK |
| Backend: `tests/unit/test_account_endpoints.py` | Contratos de endpoints account (challenge/delete) | Presente en repo |
| Backend: `tests/unit/test_account_service.py` | Soft delete y challenge service | Presente en repo |
| Backend: `tests/unit/test_auth_deleted_user.py` | Bloqueo de usuarios eliminados en auth deps | Presente en repo |
| Backend: `tests/integration/test_account_soft_delete_policy.py` | Preservacion reportes + nullify reporter_user_id | Presente en repo |
| Backend: `tests/integration/test_citizen_reports_fk_policy.py` | Enforcement FK `ON DELETE SET NULL` | Presente en repo |
| Build frontend (`npm run build`) | TypeScript + Vite | OK |

### Resultado observado en validacion local de este frente

- Suite objetivo de navegacion/footer/auth ejecutada con `vitest`: 17 tests pasando.
- `npm run build` frontend completado en verde.

## 12) Limitaciones abiertas y proximos pasos

- `ProtectedRoute` mantiene `navigate(-1)` en `onGoBack` para accesos directos a rutas protegidas. Esto convive con comportamiento de navbar locked flow (cierre de modal sin retroceso).
- En `Profile` y algunos componentes de account hay copy hardcodeado en espanol (sin usar 100% i18n keys). Recomendada normalizacion para consistencia multilanguage.
- Los tests backend estan presentes y alineados con el contrato, pero su ejecucion depende del entorno DB configurado.
- Posible mejora: centralizar microcopy de seguridad (profile/account delete) en `translations.ts` para evitar drift.
- Posible mejora: agregar seccion visual (capturas) en este README si se requiere handoff a equipo no tecnico.

## Referencias cruzadas

- Plan original del frente: `docs/menu/plan_menu.md`
- Hoja tecnica por PRs: `docs/menu/technical_tasks_menu.md`
- Flujo CI frontend: `.github/workflows/frontend-build.yml`

