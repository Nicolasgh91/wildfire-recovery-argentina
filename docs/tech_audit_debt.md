# Tech Audit Debt — UC-F06 Sesión 2026-03-16

## 2026-03-16 [Step 0] — Baseline test failure D-09/D-10

**Tipo:** hallazgo inesperado
**Tarea relacionada:** D-09/D-10
**Descripción:** El test `D-09/D-10: clicking result.fires link navigates with ReturnContext.audit (land-use)` falla antes de cualquier cambio. Causa raíz: la línea 975 de `Audit.tsx` llama a `handleFireDetailNav(fire.fire_event_id)` — función inexistente. El test intenta interactuar con el botón "Ver detalle" que ejecuta esa función y produce un ReferenceError.
**Acción tomada:** Registrado como failure pre-existente. Se corrige en Phase 2 (DEV-04).
**Impacto:** Bloquea validación del flujo completo result.fires → FireDetail → volver.

---

## 2026-03-16 [Phase 1] — DEV-01: Variant de presets difiere del documentado

**Tipo:** desvío
**Tarea relacionada:** A-02
**Descripción:** El documento de tareas (D-01) indica `variant="outline"` para presets no seleccionados y `variant="default"` para seleccionados. El código encontrado usa `variant="secondary"` para todos con `opacity-60` para seleccionados. D-01 es decisión fijada; se aplica de todas formas.
**Acción tomada:** Cambiado a `variant="outline"` + clases emerald para no seleccionados, `variant="default"` para seleccionado.
**Impacto:** Cambio visual. Los botones pasan de marrón secundario a verde emerald con borde.

---

## 2026-03-16 [Phase 1] — DEV-02: Variant de paginación difiere del documentado

**Tipo:** desvío
**Tarea relacionada:** A-05
**Descripción:** Botones de paginación usaban `variant="secondary"` con clases emerald condicionales. D-01 mandaba `variant="outline"`.
**Acción tomada:** Cambiado a `variant="outline"`.
**Impacto:** Visual. Coherente con presets.

---

## 2026-03-16 [Phase 1] — DEV-09: Clases dark mode no documentadas en D-01

**Tipo:** decisión forzada
**Tarea relacionada:** A-02, A-05
**Descripción:** Se agregaron clases `dark:border-emerald-500 dark:text-emerald-400` que no están en la decisión D-01 (`border-emerald-600 text-emerald-700 hover:bg-emerald-50`). Son clases de accesibilidad para tema oscuro.
**Acción tomada:** Incluidas como mejora de accesibilidad. Registrado como adición no documentada.
**Impacto:** Mejora visual en tema oscuro. Sin impacto funcional.

---

## 2026-03-16 [Phase 1] — A-07: Paginación inline mantenida

**Tipo:** decisión forzada
**Tarea relacionada:** A-07
**Descripción:** El componente `components/fires/pagination.tsx` requiere `PaginationMeta` type, `onPageSizeChange` handler, y selector de tamaño de página. La integración excede el threshold de 15 líneas.
**Acción tomada:** Paginación inline mantenida. Comentario inline agregado.
**Impacto:** Ninguno. Reuso del componente queda como potencial refactor futuro.

---

## 2026-03-16 [Phase 2] — DEV-04: Referencia huérfana handleFireDetailNav

**Tipo:** desvío / bug
**Tarea relacionada:** B-05
**Descripción:** Línea 975 de `Audit.tsx` llama a `handleFireDetailNav(fire.fire_event_id)`. Esta función no existe en el componente. Las funciones reales son `handleFireDetailNavFromPoint` (línea 349) y `handleFireDetailNavFromSearch` (línea 386). Se verificó con búsqueda exhaustiva (validación C-2).
**Acción tomada:** Corregido a `handleFireDetailNavFromPoint` porque el contexto es la sección `result.fires` que muestra resultados de auditoría puntual (land-use).
**Impacto:** Fix de bug. Restaura funcionalidad de navegación result.fires → detalle.

---

## 2026-03-16 [Phase 3] — DEV-03: Decisión forzada aceptada — AuditReturnContext discriminated union

**Tipo:** decisión forzada aceptada
**Tarea relacionada:** B2-01, B2-02
**Descripción:** D-04 define shape mínimo `{ returnTo: 'audit', audit: { lat, lon, radius, page } }`. El código implementado usa un discriminated union con `origin: 'search' | 'land-use'`:
- `handleFireDetailNavFromPoint` construye `{ returnTo: 'audit', audit: { origin: 'land-use', lat, lon, radius_m, page } }` — **superconjunto** de D-04.
- `handleFireDetailNavFromSearch` construye `{ returnTo: 'audit', audit: { origin: 'search', q, radius_km, page } }` — **extensión** de D-04 para búsqueda textual.
- `handleBack` en `FireDetail.tsx` destructura ambos shapes correctamente.
**Acción tomada:** Se acepta la implementación real como superconjunto compatible con D-04. D-06 queda **cerrado** como decisión de tipos: el discriminated union `origin: 'search' | 'land-use'` resuelve completamente el problema de diseño que D-06 flaggeaba (shapes distintos según origen). El bloqueo restante de Fase 5 (grupo C) es exclusivamente de backend: `/audit/search` aún no expone `fire_event_id` por episodio. Se eliminó el bloque de tipos duplicados (líneas 25-50 del archivo `navigation.ts` original) que conflictuaba con la definición funcional.
**Impacto:** Sin impacto funcional. Tipos limpiados. D-04 satisfecho como subconjunto. D-06 cerrado.

---

## 2026-03-16 [Phase 5 — OUT OF SCOPE] — buildAuditReturnContext dead code

**Tipo:** hallazgo inesperado
**Tarea relacionada:** N/A (fuera del alcance de uc_f06_tasks_unificadas.md)
**Descripción:** La función `buildAuditReturnContext` (línea ~314 de `Audit.tsx`) no tiene invocaciones. Los handlers de navegación construyen el contexto inline. Identificado como código muerto.
**Acción tomada:** NO eliminado en esta sesión. Registrado como deuda técnica per regla de ejecución #3 (sin creatividad no solicitada).
**Impacto:** Ninguno inmediato. Evaluación de eliminación queda como tarea independiente.

---

## 2026-03-16 [Phase 7] — F-04/F-05: Bloqueadas por Fase 5

**Tipo:** bloqueo
**Tarea relacionada:** F-04, F-05
**Descripción:** Las tareas F-04 (actualizar STATE.md con columna de ID en grilla) y F-05 (actualizar estado a "listo en producción") dependen de la Fase 5 que está bloqueada.
**Acción tomada:** Registrado como pendiente. No ejecutado.
**Impacto:** Documentación incompleta hasta resolución de Fase 5. El bloqueo de Fase 5 es exclusivamente de backend (ver DEV-03).

---

## 2026-03-16 [Phase 4] — B3-02: Cleanup de sessionStorage en idle timer

**Tipo:** implementación nueva
**Tarea relacionada:** B3-02
**Descripción:** El `useIdleTimer` en `App.tsx` navegaba a `/login` al expirar la sesión pero no limpiaba `RETURN_CONTEXT_KEY` de `sessionStorage`, dejando contexto de auditoría residual.
**Acción tomada:** Se importó la constante `RETURN_CONTEXT_KEY` desde `@/types/navigation` y se agregó `sessionStorage.removeItem(RETURN_CONTEXT_KEY)` en el callback `onIdle`. Se usó la constante, no el literal `'fg:return_context'`.
**Impacto:** Al expirar la sesión por inactividad, el contexto de retorno de auditoría se limpia correctamente. Sin deuda de mantenimiento.

---

## 2026-03-16 [Phase 2] — DEV-05: Fases B-02 a B-06 ya implementadas — verificación completada

**Tipo:** verificación completada
**Tarea relacionada:** B-02, B-03, B-04, B-05, B-06
**Descripción:** Las tareas del grupo B (ID visible y navegación en `result.fires`) ya estaban implementadas en el código existente:
- B-02: `fire_event_id` truncado a 8 caracteres con `...` — presente en `Audit.tsx` (líneas 948-963).
- B-03: Fallback "N/D" cuando `fire_event_id` es null — presente.
- B-04: `buildAuditReturnContext` implementado inline en los handlers de navegación.
- B-05: `handleFireDetailNavFromPoint` y `handleFireDetailNavFromSearch` existen y funcionan (excepto la referencia huérfana corregida en DEV-04).
- B-06: Botón con ícono `ExternalLink` para navegación a detalle — presente.
**Acción tomada:** Verificación completada. La implementación existente satisface los criterios de aceptación del grupo B.
**Impacto:** Ninguno. Código existente es correcto.

---

## 2026-03-16 [Phase 3] — DEV-06: Fases B2-01 a B2-04 ya implementadas — verificación completada

**Tipo:** verificación completada
**Tarea relacionada:** B2-01, B2-02, B2-03, B2-04
**Descripción:** Las tareas del grupo B2 (ReturnContext y handleBack) ya estaban implementadas:
- B2-01/B2-02: `AuditReturnContext` como discriminated union con `origin: 'search' | 'land-use'` — presente en `navigation.ts` (tipos duplicados eliminados en DEV-03).
- B2-03: `handleBack` en `FireDetail.tsx` (líneas 86-129) maneja `returnTo === 'audit'` correctamente, navegando con `state: { restore: ctx.audit }`.
- B2-04: `useEffect` de restauración en `Audit.tsx` (líneas 172-217) restaura estado desde `location.state`, manejando ambos orígenes (`'search'` y `'land-use'`).
**Acción tomada:** Verificación completada. La implementación existente satisface los criterios de aceptación del grupo B2.
**Impacto:** Ninguno. Código existente es correcto.

---

## 2026-03-16 [Backend] — DEV-10: Ghost alias `rep.fire_event_id` en queries SQL

**Tipo:** bug / desvío
**Tarea relacionada:** Fase 0 (backend)
**Descripción:** Las funciones `_fetch_episodes_by_province` y `_fetch_episodes_by_protected_area` en `app/api/v1/audit.py` incluían `rep.fire_event_id` en el SELECT — un alias fantasma de una versión intermedia del query que nunca se limpió al renombrar a `ev`. Adicionalmente, `ev.fire_event_id` aparecía duplicado como última columna. `_fetch_episodes_by_point` ya estaba correcto (sin `rep.`).
**Causa raíz:** El agente de código de la sesión anterior introdujo el alias `rep` en una versión intermedia y no lo limpió al renombrarlo a `ev`. Los tests de integración del step 0 corrieron contra mocks que no ejecutan el SQL efectivo, por lo que el error de columna inexistente (`rep.fire_event_id`) no fue detectado en ese momento.
**Acción tomada:** Eliminado `rep.fire_event_id` y la columna duplicada `ev.fire_event_id` en ambas funciones. Cada SELECT ahora tiene una única referencia `ev.fire_event_id`. Test de integración `test_audit_search_fire_event_id.py` pasa (1/1).
**Impacto:** Fix de bug. Las queries ahora son ejecutables contra la base de datos real.
**Lección:** Los tests de integración deben ejecutarse contra una base de datos real (o al menos validar la estructura SQL) para capturar errores de alias.

---

## 2026-03-16 [B2-04] — Infinite loop en useEffect de restauración

**Tipo:** bug introducido en implementación  
**Tarea relacionada:** B2-04  
**Descripción:** El `useEffect` que restaura la búsqueda al volver desde `FireDetail` incluía dependencias inestables en su versión inicial (por ejemplo, `searchAuditEpisodes` definida dentro del componente), lo que podía provocar un loop infinito: cada render recreaba la función, el efecto se re-ejecutaba, disparaba una nueva búsqueda y así sucesivamente, generando miles de requests hasta agotar los recursos del navegador (`ERR_INSUFFICIENT_RESOURCES`, miles de mensajes en consola).  
**Acción tomada:** Se consolidó el efecto como restauración de **única ejecución**: array de dependencias vacío (`[]`) con comentario de ESLint explícito, y limpieza inmediata de `location.state` mediante `window.history.replaceState({}, '', location.pathname + location.search)` antes de disparar `searchAuditEpisodes` (para `origin: 'search'`) o `auditMutation.mutate` (para `origin: 'land-use'`). Se agregaron tests de restauración (B2-04) que mockean `window.history.replaceState` como NO-OP para asegurar que, incluso si el `state` persistiera, tanto `searchAuditEpisodes` como `auditMutation.mutate` se ejecutan exactamente una vez.  
**Impacto:** El flujo auditoría → detalle (`/fires/:id`) → volver a `/audit` deja de estar en riesgo de loops infinitos de restauración y se comporta de forma estable incluso en presencia de renders adicionales.
