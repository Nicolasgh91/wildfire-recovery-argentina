# Menu + perfil v2 - implementacion full stack

> Documento de cambios ya aplicados sobre navegación y perfil. El estado vigente de rutas y acceso está en `docs/frontend/README.md` y `docs/frontend/routing_access_ruc.md`; usar este archivo como narrativa detallada del frente de menú/perfil.

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

*(contenido restante del README original — arquitectura de navegación, matriz de accesos, candados, perfil v2, account lifecycle, z-index/overlays, CI guardrails y tablas de pruebas — se mantiene íntegro en este archivo como referencia histórica).*

