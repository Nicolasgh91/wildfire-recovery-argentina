# UC-F06 — Página de auditoría: tareas técnicas unificadas

> Consolidación de: `audit_update_plan.md`, `audit-search-debug-findings.md`, `lessons.md`, `tasks_UC-06.md`, `uc_f06_technical_tasks.md`.  
> Fecha de consolidación: 2026-03-16.  
> Criterio de jerarquía: schema → flow logic → workers → API → UI.

---

## Estado general

| Capa | Componente | Estado |
|------|-----------|--------|
| API | `GET /audit/search` con `fire_event_id` | ✅ Completo |
| API | Schema `AuditSearchEpisode` (backend) | ✅ Completo |
| UI | Tipo `AuditSearchEpisode` (frontend) | ✅ Completo |
| UI | Presets de área — color verde | ⬜ Pendiente |
| UI | Paginación de grilla — color verde | ⬜ Pendiente |
| UI | ID visible en `result.fires` | ⬜ Pendiente |
| UI | Navegación clickeable a `/fires/:id` | ⬜ Pendiente |
| UI | `ReturnContext` origen `audit` | ⬜ Pendiente |
| UI | Columna ID en grilla de episodios | 🔴 Bloqueada (backend pendiente) |
| Testing | Tests D-01 a D-10 (grupos A y B) | ⬜ Pendiente |
| Testing | Tests D-11 a D-14 (grupo C) | 🔴 Bloqueada por grupo C |
| Docs | ADR + backlog + STATE.md | ⬜ Pendiente |

---

## Decisiones fijadas (no reabrir)

| ID | Decisión | Fecha |
|----|----------|-------|
| D-01 | Color: opción A — clases `border-emerald-600 text-emerald-700 hover:bg-emerald-50` sobre `variant="outline"`. Sin variante nueva. | 2026-03-16 |
| D-02 | ID en `result.fires` usando `fire_event_id` de `AuditFire`. Grilla de episodios no recibe columna de ID en esta iteración: `episode.id` no es apto como ID legal. | 2026-03-16 |
| D-03 | Responsividad: sin lógica condicional por breakpoint. El scroll horizontal existente (`min-w-[980px]`, `overflow-x-auto`) mitiga el riesgo. No se agrega columna a la grilla de 8 columnas. | 2026-03-16 |
| D-04 | `ReturnContext` con origen `audit`; shape: `{ returnTo: 'audit', audit: { lat, lon, radius, page } }`. Nunca guardar resultados ni textos de búsqueda en `sessionStorage` (ley 25.326). | 2026-03-16 |
| D-05 | Backend caso B: `LEFT JOIN LATERAL` vía `fire_episode_events` + `fire_events`; criterio `max_frp DESC, start_date ASC`. | 2026-03-16 |
| D-06 | Pendiente: shape de `ReturnContext.audit` difiere según origen (textual vs. puntual). Resolver en PRE-C-01 y PRE-C-02 antes de implementar grupo C. | 2026-03-16 |

---

## Hallazgo de debugging activo

**Síntoma:** requests a `/audit/search` no visibles en Network tab; errores ocultos en UI.

**Causa raíz identificada** (`audit-search-debug-findings.md`):
- El bloque `catch` en `handleSubmit` y en la restauración desde `FireDetail` suprime el error real: solo llama a `setLocalError(t('geocodeNotFound'))` sin `console.error`.
- Causas posibles que no generan request: guard `status !== 'authenticated'` activo, formulario inválido (`form.formState.isValid === false`), o excepción síncrona antes de que axios envíe.

**Corrección mínima aplicada:**
```typescript
// handleSubmit — catch
catch (error) {
  console.error('searchAuditEpisodes failed', error);
  setLocalError(t('geocodeNotFound'));
}

// Restore desde FireDetail — catch
.catch((error) => {
  console.error('restore searchAuditEpisodes failed', error);
  setLocalError(t('geocodeNotFound'));
})
```

**Tests:** 4/4 pasan en `frontend/src/pages/__tests__/AuditPage.test.tsx`.  
**Estado:** ✅ Corrección aplicada. Pendiente validación manual en navegador (ver grupo E).

---

## Fase 0 — Backend `/audit/search` con `fire_event_id`

> Estado: **completo**. Registrado para trazabilidad.

| # | Tarea | Estado |
|---|-------|--------|
| 0-1 | Extender `AuditSearchEpisode` con `fire_event_id: Optional[UUID] = None` en `app/schemas/audit.py` | ✅ |
| 0-2 | `_fetch_episodes_by_province` con `LEFT JOIN LATERAL`, criterio `max_frp DESC, start_date ASC` | ✅ |
| 0-3 | `_fetch_episodes_by_protected_area` con el mismo join | ✅ |
| 0-4 | `_fetch_episodes_by_point` con el mismo join | ✅ |
| 0-5 | Serialización `null` (no omisión) para `fire_event_id` sin valor | ✅ |
| 0-6 | Índices existentes verificados; sin migración nueva | ✅ |
| 0-7 | `tests/integration/test_audit_search_fire_event_id.py` (cubre caso con ID y caso con `null`) | ✅ |
| 0-8 | Tipo `fire_event_id?: string \| null` en `frontend/src/types/audit-search.ts` | ✅ |

**Lección registrada:** el campo `fire_event_id` se resuelve mediante `LEFT JOIN LATERAL` entre `fire_episodes`, `fire_episode_events` y `fire_events`. El schema backend y el tipo frontend deben exponer siempre la clave (como `null` si no hay valor, nunca omitida). Cualquier cambio en el SQL debe ejecutarse junto con los tests de integración y los tests de UI D-11 a D-14.

---

## Fase 1 — UI: presets de área y paginación (grupo A)

> Sin dependencias de backend ni de navegación. **Ejecutar en paralelo con fase 2.**

| # | Tarea | Archivo | Estado |
|---|-------|---------|--------|
| A-01 | Localizar bloque `AREA_PRESETS` en `Audit.tsx` | `frontend/src/pages/Audit.tsx` | ⬜ |
| A-02 | Agregar `border-emerald-600 text-emerald-700 hover:bg-emerald-50` a los botones con `variant="outline"` (no seleccionados). El botón seleccionado (`variant="default"`) **no** recibe estas clases. | `Audit.tsx` | ⬜ |
| A-03 | Verificar accesibilidad: foco visible, contraste en hover/active, estado `disabled` | `Audit.tsx` | ⬜ |
| A-04 | Localizar botones "Anterior" / "Siguiente" de paginación | `Audit.tsx` | ⬜ |
| A-05 | Agregar las mismas clases emerald a los botones de paginación | `Audit.tsx` | ⬜ |
| A-06 | Confirmar que `disabled` desactiva el verde (opacidad, cursor) en primera y última página | `Audit.tsx` | ⬜ |
| A-07 | Evaluar reutilización de `frontend/src/components/fires/pagination.tsx`. Solo reemplazar si la integración requiere ≤ 15 líneas de cambio; si no, documentar decisión en comentario inline. | `Audit.tsx` | ⬜ |

**Criterio de aceptación:**
- Los 3 botones de área muestran verde en estado no seleccionado; el seleccionado mantiene diferenciación visual sin mezclar estilos.
- Los botones de paginación muestran verde consistente con los presets.
- El estado `disabled` no muestra verde.

---

## Fase 2 — UI: ID visible y navegación en `result.fires` (grupo B)

> Depende de D-02 y D-04 (fijadas). **Ejecutar en paralelo con fase 1.**

| # | Tarea | Archivo | Estado |
|---|-------|---------|--------|
| B-01 | Localizar bloque `result.fires` en `Audit.tsx` | `Audit.tsx` | ⬜ |
| B-02 | Mostrar `fire_event_id` truncado (8 chars + `...`) con `title` del ID completo. Etiqueta: "ID de incendio". Clase: `text-xs font-mono text-muted-foreground`. | `Audit.tsx` | ⬜ |
| B-03 | Si `fire_event_id` es `null` o vacío: mostrar "N/D", no renderizar link. | `Audit.tsx` | ⬜ |
| B-04 | Extraer función `buildAuditReturnContext` con parámetros `lat`, `lon`, `radius_m`, `currentPage` | `Audit.tsx` | ⬜ |
| B-05 | Implementar `handleFireDetailNav(fireEventId)`: guarda en `sessionStorage` y pasa en `state` a `navigate` | `Audit.tsx` | ⬜ |
| B-06 | Agregar botón/link explícito por ítem (ícono `ExternalLink`, tooltip "Ver detalle del incendio"). Solo renderizar cuando `fire_event_id` existe. | `Audit.tsx` | ⬜ |

**Implementación de referencia para B-05:**
```typescript
const handleFireDetailNav = (fireEventId: string) => {
  const ctx: AuditReturnContext = {
    returnTo: 'audit',
    audit: {
      lat: searchParams.lat,
      lon: searchParams.lon,
      radius: searchParams.radius,
      page: currentPage,
    },
  };
  sessionStorage.setItem(RETURN_CONTEXT_KEY, JSON.stringify(ctx));
  navigate(`/fires/${encodeURIComponent(fireEventId)}`, { state: ctx });
};
```

---

## Fase 3 — Extensión de `ReturnContext` y `handleBack` (grupo B2)

> Depende de B-04 y B-05 (fase 2).

| # | Tarea | Archivo | Estado |
|---|-------|---------|--------|
| B2-01 | Agregar tipo `AuditReturnContext` en `navigation.ts` (ver D-04) | `frontend/src/types/navigation.ts` | ⬜ |
| B2-02 | Incluir `AuditReturnContext` en el union type de `ReturnContext` | `navigation.ts` | ⬜ |
| B2-03 | Agregar caso `returnTo === 'audit'` en `handleBack` de `FireDetail.tsx` | `frontend/src/pages/FireDetail.tsx` | ⬜ |
| B2-04 | Verificar que `Audit.tsx` lee `location.state?.restore` para repoblar filtros y página al volver. Si no lo hace, agregar ese comportamiento. | `Audit.tsx` | ⬜ |

**Tipo de referencia (D-04):**
```typescript
type AuditReturnContext = {
  returnTo: 'audit';
  audit: {
    lat: number;
    lon: number;
    radius: number;
    page: number;
  };
};
```

**Caso en `handleBack`:**
```typescript
case 'audit':
  navigate('/audit', {
    state: {
      restore: {
        lat: ctx.audit.lat,
        lon: ctx.audit.lon,
        radius: ctx.audit.radius,
        page: ctx.audit.page,
      },
    },
  });
  break;
```

---

## Fase 4 — Guard de autenticación y limpieza de contexto (grupo B3)

> Depende de B2-03 (fase 3).

| # | Tarea | Archivo | Estado |
|---|-------|---------|--------|
| B3-01 | Confirmar que el guard de `/audit` cubre también el link de navegación a `/fires/:id` | `Audit.tsx` + guard | ⬜ |
| B3-02 | Verificar comportamiento si la sesión expira entre búsqueda y click: redirección a login sin `ReturnContext` residual | `FireDetail.tsx` + guard | ⬜ |

**Criterio de aceptación:**
- Sesión válida: flujo auditoría → detalle → volver funciona completo.
- Sesión expirada: redirección a login; no queda contexto de auditoría en `sessionStorage`.

---

## Fase 5 — Resolución de D-06 y columna ID en grilla de episodios (grupo PRE-C + C)

> **Bloqueada por D-06.** Requiere completar fases 3 y 4 primero.  
> También bloqueada por backend: `/audit/search` debe exponer `fire_event_id` por episodio (ver ítem de backlog en fase 8).

### Paso previo obligatorio (desbloquea grupo C)

| # | Tarea | Estado |
|---|-------|--------|
| PRE-C-01 | Inspeccionar `Audit.tsx`: qué estado/parámetros disponibles en búsqueda textual (`/audit/search`) vs. puntual (`/audit/land-use`) | ⬜ |
| PRE-C-02 | Definir y documentar los dos shapes de `ReturnContext.audit`: textual `{ q, page }` y puntual `{ lat, lon, radius_m, page }`. Actualizar D-06. | ⬜ |
| PRE-C-03 | Actualizar `buildAuditReturnContext` para manejar ambos shapes según el origen activo | ⬜ |

### Implementación columna ID (grupo C)

| # | Tarea | Archivo | Estado |
|---|-------|---------|--------|
| C-01 | Agregar `TableHead` "ID de incendio" en grilla de episodios. Posición: penúltima columna (antes de acción). | `Audit.tsx` | ⬜ |
| C-02 | Renderizar `episode.fire_event_id` truncado (8 chars + `...`) con `title` del ID completo. Clase: `text-[11px] font-mono text-muted-foreground`. | `Audit.tsx` | ⬜ |
| C-03 | Mostrar "N/D" cuando `fire_event_id` es `null` | `Audit.tsx` | ⬜ |
| C-04 | Agregar botón/link `ExternalLink` en la celda, solo cuando `fire_event_id` existe. Reutilizar `handleFireDetailNav` con el shape correcto de PRE-C-02. | `Audit.tsx` | ⬜ |
| C-05 | Confirmar que la tabla sigue funcionando con scroll horizontal (`min-w-[980px]`, `overflow-x-auto`) con 9 columnas | `Audit.tsx` | ⬜ |

---

## Fase 6 — Testing (grupos D y E)

> D-01 a D-10: desbloqueados tras completar fases 1 y 2.  
> D-11 a D-14: desbloqueados tras completar fase 5.  
> E-01 a E-06: verificación manual tras completar todas las fases de implementación.

### Tests automatizados

| # | Test | Archivo | Estado |
|---|------|---------|--------|
| D-01 | Crear/ampliar suite de `AuditPage.test.tsx` | `__tests__/AuditPage.test.tsx` | ⬜ |
| D-02 | Presets no seleccionados tienen `border-emerald-600 text-emerald-700` | ídem | ⬜ |
| D-03 | Preset seleccionado no tiene clases emerald de outline | ídem | ⬜ |
| D-04 | Paginación — botón "Anterior" con `disabled` en primera página | ídem | ⬜ |
| D-05 | Paginación — botón "Siguiente" con `disabled` en última página | ídem | ⬜ |
| D-06 | Paginación — ambos botones habilitados en página intermedia | ídem | ⬜ |
| D-07 | ID en `result.fires` — truncado visible, `title` con ID completo | ídem | ⬜ |
| D-08 | `result.fires` sin `fire_event_id` — muestra "N/D", no renderiza link | ídem | ⬜ |
| D-09 | Click en link — `navigate` recibe `/fires/:id` correcto y `ReturnContext` con `returnTo: 'audit'` | ídem | ⬜ |
| D-10 | `sessionStorage` contiene solo `lat`, `lon`, `radius`, `page`. Sin resultados ni textos (ley 25.326). | ídem | ⬜ |
| D-11 | Grilla de episodios — header "ID de incendio" presente | ídem | 🔴 Requiere fase 5 |
| D-12 | Grilla de episodios — fila con `fire_event_id` muestra ID truncado y link | ídem | 🔴 Requiere fase 5 |
| D-13 | Grilla de episodios — fila sin `fire_event_id` muestra "N/D", sin link | ídem | 🔴 Requiere fase 5 |
| D-14 | Navegación desde grilla — `ReturnContext` usa shape textual `{ q, page }` cuando corresponde | ídem | 🔴 Requiere PRE-C-02 + fase 5 |

### Verificación manual de regresiones (grupo E)

| # | Escenario | Estado |
|---|-----------|--------|
| E-01 | `/audit` en desktop ≥ 1280px: presets y paginación con verde consistente | ⬜ |
| E-02 | `/audit` en mobile < 768px: grilla con scroll sin ruptura; `result.fires` legible con ID y link | ⬜ |
| E-03 | Tema oscuro (si aplica): contraste suficiente del verde emerald | ⬜ |
| E-04 | Flujo sin cambios: `/` → `/fires/:id` → volver | ⬜ |
| E-05 | Flujo sin cambios: `/fires/history` → `/fires/:id` → volver | ⬜ |
| E-06 | Flujo sin cambios: `/map` → `/fires/:id` → volver | ⬜ |
| E-07 | Verificación debugging: usuario autenticado busca "Chubut" con radio 1 km → aparece `GET .../audit/search?q=Chubut&limit=20&radius_km=1` en Network; si falla, `searchAuditEpisodes failed` visible en Console. | ⬜ |
| E-08 | Usuario no autenticado en `/audit` → mensaje "authRequired" sin request a `/audit/search` en Network | ⬜ |

---

## Fase 7 — Documentación y backlog (grupo F)

| # | Tarea | Archivo | Estado |
|---|-------|---------|--------|
| F-01 | Registrar ADR de origen `audit` en `ReturnContext`. Incluir los dos shapes (textual y puntual) tras resolver PRE-C-02. Restricción ley 25.326 explícita. | `docs/decisions/adr.md` | ⬜ |
| F-02 | Registrar en backlog ítem bloqueante: ampliar `/audit/search` para exponer `fire_event_id` por episodio (prerrequisito de grilla con ID legal). | `docs/tasks/backlog.md` | ⬜ |
| F-03 | Actualizar `STATE.md` sección UC-F06 — estilos, ID en `result.fires`, navegación (tras despliegue de fases 1–4). | `docs/STATE.md` | ⬜ |
| F-04 | Actualizar `STATE.md` sección UC-F06 — columna de ID en grilla de episodios (tras despliegue de fase 5). | `docs/STATE.md` | ⬜ |
| F-05 | Actualizar `docs/product/casos-de-uso-y-estado.md` — estado UC-F06 a "listo en producción" tras despliegue completo. | `casos-de-uso-y-estado.md` | ⬜ |
| F-06 | Registrar mejoras pendientes de responsividad identificadas durante implementación. | `docs/tasks/backlog.md` | ⬜ |

---

## Roadmap visual

```
✅ Fase 0 — Backend /audit/search (completo)
✅ Debugging — console.error en catch (aplicado)

▶ Fase 1 — UI presets y paginación (grupo A) ─────┐ paralelo
▶ Fase 2 — ID + navegación result.fires (grupo B) ─┘

▶ Fase 3 — ReturnContext + handleBack (grupo B2) — depende de fase 2
▶ Fase 4 — Guard de autenticación (grupo B3)    — depende de fase 3

○ Fase 6 — Testing D-01..D-10 + E              — depende de fases 1–4

◇ Fase 5 — Columna ID en grilla episodios      — bloqueada:
           (grupo PRE-C + C)                     (1) resolver D-06
                                                 (2) backend: fire_event_id en /audit/search

○ Fase 6 — Testing D-11..D-14                  — depende de fase 5
○ Fase 7 — Documentación y backlog             — F-01..F-03 paralelo; F-04..F-05 tras fase 5
```

---

## Contrato invariante (no romper)

- `AuditSearchEpisode.fire_event_id` siempre presente en el JSON (como `null` si no hay valor, nunca omitido).
- `sessionStorage` solo contiene parámetros compactos; nunca listas de resultados ni textos de búsqueda (ley 25.326).
- El ID mostrado en UI es exactamente el mismo que el usado para navegar a `/fires/:id` (integridad legal, ley 26.815).
- Los flujos de retorno existentes (`home`, `history`, `map`) no se alteran en ninguna fase.

---

*Generado: 2026-03-16. Fuentes: `audit_update_plan.md`, `audit-search-debug-findings.md`, `lessons.md`, `tasks_UC-06.md`, `uc_f06_technical_tasks.md`.*
