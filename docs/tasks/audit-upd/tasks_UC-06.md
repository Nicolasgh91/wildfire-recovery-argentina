# UC-F06 — Tareas técnicas con estado de avance

> El agente debe marcar cada tarea con `[x]` al completarla y registrar una nota breve si hubo desvíos o decisiones durante la ejecución.  
> No avanzar a un grupo sin que el grupo bloqueante esté completo.

---

## Leyenda de estado

| Símbolo | Significado |
|---------|-------------|
| `[x]` | Completada |
| `[ ]` | Pendiente |
| `[~]` | En progreso |
| `[!]` | Bloqueada — ver nota |
| `[-]` | Descartada — ver nota |

---

## Historial de decisiones fijadas

| ID | Decisión | Fecha |
|----|----------|-------|
| D-01 | Color: opción A — clases emerald sobre `variant="outline"` sin variante nueva | 2026-03-16 |
| D-02 | ID en `result.fires` usando `fire_event_id` de `AuditFire`; grilla de episodios espera backend | 2026-03-16 |
| D-03 | Responsividad: sin lógica condicional por breakpoint; scroll horizontal existente | 2026-03-16 |
| D-04 | `ReturnContext` con origen `audit`; campos mínimos; nunca guardar resultados en `sessionStorage` | 2026-03-16 |
| D-05 | Backend Caso B: `LEFT JOIN LATERAL` vía `fire_episode_events` + `fire_events`; criterio `max_frp DESC, start_date ASC` | 2026-03-16 |
| D-06 | **Pendiente de resolución:** shape de `ReturnContext.audit` difiere según origen de búsqueda (textual vs. puntual); el agente debe inspeccionar `Audit.tsx` y definir los dos shapes antes de implementar iteración 2 de UI | 2026-03-16 |

---

## Grupo 0 — Backend `/audit/search` con `fire_event_id`

> **Estado: completo.** Registrado para trazabilidad.

| # | Tarea | Estado | Nota |
|---|-------|--------|------|
| 0-1 | Extender `AuditSearchEpisode` con `fire_event_id: Optional[UUID] = None` en `app/schemas/audit.py` | `[x]` | Caso B aplicado; no existe `representative_event_id` en `fire_episodes` |
| 0-2 | Actualizar `_fetch_episodes_by_province` con `LEFT JOIN LATERAL` y criterio `max_frp DESC, start_date ASC` | `[x]` | Índices existentes reutilizados |
| 0-3 | Actualizar `_fetch_episodes_by_protected_area` con el mismo join y criterio | `[x]` | Ídem |
| 0-4 | Actualizar `_fetch_episodes_by_point` con el mismo join y criterio | `[x]` | Ídem |
| 0-5 | Confirmar serialización `null` (no omisión) para `fire_event_id` sin valor | `[x]` | Verificado: campo presente como `null` en JSON |
| 0-6 | Verificar índices existentes (`idx_fire_episode_events_episode_id`, PK `fire_events.id`) | `[x]` | Sin migración nueva requerida |
| 0-7 | Agregar `tests/integration/test_audit_search_fire_event_id.py` | `[x]` | Cubre caso con ID y caso con `null` |
| 0-8 | Extender `AuditSearchEpisode` en `frontend/src/types/audit-search.ts` con `fire_event_id?: string \| null` | `[x]` | Sin uso en UI aún |

---

## Grupo A — Ajustes de UI: presets de área y paginación

> **Desbloqueado.** Sin dependencias de backend ni de navegación.

| # | Tarea | Estado | Nota |
|---|-------|--------|------|
| A-01 | Localizar bloque de `AREA_PRESETS` en `Audit.tsx` | `[ ]` | |
| A-02 | Agregar clases `border-emerald-600 text-emerald-700 hover:bg-emerald-50` a los botones no seleccionados (`variant="outline"`) | `[ ]` | Verificar que el botón seleccionado (`variant="default"`) no recibe estas clases |
| A-03 | Verificar accesibilidad: foco visible, contraste en hover/active, estado disabled | `[ ]` | |
| A-04 | Localizar botones "Anterior" / "Siguiente" de paginación en `Audit.tsx` | `[ ]` | |
| A-05 | Agregar las mismas clases emerald a los botones de paginación | `[ ]` | |
| A-06 | Confirmar que `disabled` desactiva el verde (opacidad, cursor) en primera y última página | `[ ]` | |
| A-07 | Evaluar reutilización de `frontend/src/components/fires/pagination.tsx` | `[ ]` | Solo reemplazar si la integración requiere ≤ 15 líneas de cambio; documentar decisión en comentario inline si se mantiene la paginación propia |

---

## Grupo B — ID visible y navegación clickeable en `result.fires`

> **Desbloqueado.** Depende de D-02 y D-04 (fijadas).

| # | Tarea | Estado | Nota |
|---|-------|--------|------|
| B-01 | Localizar bloque de `result.fires` en `Audit.tsx` | `[ ]` | |
| B-02 | Agregar ID truncado (8 chars + `...`) con `title` del ID completo por cada ítem de `AuditFire` | `[ ]` | Clase: `text-xs font-mono text-muted-foreground`; etiquetar como "ID de incendio" |
| B-03 | Confirmar que el ID mostrado es exactamente el `fire_event_id` que se usará en navegación | `[ ]` | |
| B-04 | Política de ausencia: si `fire_event_id` es `null` o vacío, mostrar "N/D" y no renderizar link | `[ ]` | |
| B-05 | Extraer función `buildAuditReturnContext` para construcción del contexto de retorno | `[ ]` | Ver D-06: usar parámetros de `/audit/land-use` (`lat`, `lon`, `radius_m`, `currentPage`) para `result.fires` |
| B-06 | Implementar `handleFireDetailNav(fireEventId)` usando `buildAuditReturnContext` | `[ ]` | Guarda en `sessionStorage` y pasa en `state` a `navigate` |
| B-07 | Agregar botón/link explícito por ítem de `result.fires` (ícono `ExternalLink` con tooltip "Ver detalle del incendio") | `[ ]` | No usar texto "Ver" suelto — ambiguo en contexto legal |
| B-08 | Confirmar que el botón solo se renderiza cuando `fire_event_id` existe | `[ ]` | |

---

## Grupo B2 — Extensión de `ReturnContext` y `handleBack`

> **Desbloqueado.** Depende de B-05 y B-06.

| # | Tarea | Estado | Nota |
|---|-------|--------|------|
| B2-01 | Agregar tipo `AuditReturnContext` en `frontend/src/types/navigation.ts` | `[ ]` | Ver D-06: definir shape según origen antes de tipar |
| B2-02 | Incluir `AuditReturnContext` en el union type de `ReturnContext` | `[ ]` | |
| B2-03 | Agregar caso `returnTo === 'audit'` en `handleBack` de `FireDetail.tsx` | `[ ]` | Navegar a `/audit` con `state.restore` conteniendo los parámetros del contexto |
| B2-04 | Verificar que `Audit.tsx` lee `location.state?.restore` para repoblar filtros y página al volver | `[ ]` | Si no lo hace hoy, agregar ese comportamiento |

---

## Grupo B3 — Guard de autenticación y limpieza de contexto

> **Desbloqueado.** Depende de B2-03.

| # | Tarea | Estado | Nota |
|---|-------|--------|------|
| B3-01 | Confirmar que el guard de `/audit` cubre también el link de navegación a `/fires/:id` | `[ ]` | |
| B3-02 | Verificar comportamiento si la sesión expira entre búsqueda y click: redirección a login sin `ReturnContext` residual | `[ ]` | |

---

## Grupo C — Iteración 2 de UI: columna de ID en grilla de episodios

> **Bloqueada por D-06.** El agente debe resolver el shape del `ReturnContext` para búsqueda textual antes de implementar.

### Paso previo obligatorio (desbloquea C)

| # | Tarea | Estado | Nota |
|---|-------|--------|------|
| PRE-C-01 | Inspeccionar `Audit.tsx` para determinar qué estado/parámetros están disponibles cuando el usuario llega vía búsqueda textual (`/audit/search`) vs. búsqueda puntual (`/audit/land-use`) | `[ ]` | |
| PRE-C-02 | Definir y documentar los dos shapes de `ReturnContext.audit`: uno para origen textual (`{ q, page }`), otro para origen puntual (`{ lat, lon, radius_m, page }`) | `[ ]` | Actualizar D-06 con la decisión tomada |
| PRE-C-03 | Actualizar `buildAuditReturnContext` para manejar ambos shapes según el origen activo | `[ ]` | |

### Tareas de implementación (desbloqueadas tras PRE-C)

| # | Tarea | Estado | Nota |
|---|-------|--------|------|
| C-01 | Agregar `TableHead` "ID de incendio" en la grilla de episodios de `Audit.tsx` | `[ ]` | Posición: penúltima columna (antes de la acción), no primera — ver observación de UX en revisión |
| C-02 | Renderizar `episode.fire_event_id` truncado (8 chars + `...`) con `title` del ID completo por fila | `[ ]` | Clase: `text-[11px] font-mono text-muted-foreground` |
| C-03 | Mostrar "N/D" cuando `fire_event_id` es `null` | `[ ]` | |
| C-04 | Agregar botón/link "Ver detalle del incendio" (ícono `ExternalLink`) en la misma celda de ID, solo cuando `fire_event_id` existe | `[ ]` | Reutilizar `handleFireDetailNav` con el shape correcto de `ReturnContext` según PRE-C-02 |
| C-05 | Confirmar que la tabla sigue funcionando con scroll horizontal (`min-w-[980px]`, `overflow-x-auto`) con 9 columnas | `[ ]` | Sin lógica condicional por breakpoint |

---

## Grupo D — Testing

> **Desbloqueado** para tareas de grupos A y B. Desbloqueado para C tras completar grupo C.

| # | Tarea | Estado | Nota |
|---|-------|--------|------|
| D-01 | Crear/ampliar `frontend/src/pages/__tests__/AuditPage.test.tsx` | `[ ]` | |
| D-02 | Test: presets de área no seleccionados tienen clases `border-emerald-600 text-emerald-700` | `[ ]` | |
| D-03 | Test: preset seleccionado no tiene clases emerald de outline | `[ ]` | |
| D-04 | Test: paginación — botón "Anterior" con `disabled` en primera página | `[ ]` | |
| D-05 | Test: paginación — botón "Siguiente" con `disabled` en última página | `[ ]` | |
| D-06 | Test: paginación — ambos botones habilitados en página intermedia | `[ ]` | |
| D-07 | Test: ID de incendio en `result.fires` — truncado visible, `title` con ID completo | `[ ]` | |
| D-08 | Test: `result.fires` sin `fire_event_id` — muestra "N/D", no renderiza link | `[ ]` | |
| D-09 | Test: click en link de `result.fires` — `navigate` recibe `/fires/:id` correcto y `ReturnContext` con `returnTo: 'audit'` | `[ ]` | |
| D-10 | Test: `sessionStorage` contiene solo campos mínimos — sin listas de resultados ni textos de búsqueda | `[ ]` | Verificar cumplimiento ley 25.326 |
| D-11 | Test: grilla de episodios — header "ID de incendio" presente | `[ ]` | Requiere grupo C completo |
| D-12 | Test: grilla de episodios — fila con `fire_event_id` muestra ID truncado y link de detalle | `[ ]` | Requiere grupo C completo |
| D-13 | Test: grilla de episodios — fila sin `fire_event_id` muestra "N/D" y no renderiza link | `[ ]` | Requiere grupo C completo |
| D-14 | Test: navegación desde grilla de episodios — `ReturnContext` usa shape textual (`{ q, page }`) cuando corresponde | `[ ]` | Requiere PRE-C-02 y grupo C completo |

---

## Grupo E — Verificación manual de regresiones visuales

| # | Tarea | Estado | Nota |
|---|-------|--------|------|
| E-01 | Revisar `/audit` en desktop (≥ 1280px): presets y paginación con verde consistente | `[ ]` | |
| E-02 | Revisar `/audit` en mobile (< 768px): grilla con scroll horizontal sin ruptura; `result.fires` legible con ID y link | `[ ]` | |
| E-03 | Revisar tema oscuro (si aplica): contraste suficiente del verde emerald | `[ ]` | |
| E-04 | Verificar flujos existentes sin cambios: `/` → `/fires/:id` → volver | `[ ]` | |
| E-05 | Verificar flujos existentes sin cambios: `/fires/history` → `/fires/:id` → volver | `[ ]` | |
| E-06 | Verificar flujos existentes sin cambios: `/map` → `/fires/:id` → volver | `[ ]` | |

---

## Grupo F — Documentación y cierre

| # | Tarea | Estado | Nota |
|---|-------|--------|------|
| F-01 | Registrar ADR de origen `audit` en `ReturnContext` en `docs/decisions/adr.md` | `[ ]` | Incluir los dos shapes (textual y puntual) una vez resuelto PRE-C-02 |
| F-02 | Registrar en `docs/tasks/backlog.md` cualquier pendiente de responsividad o mejora identificada durante implementación | `[ ]` | |
| F-03 | Actualizar `docs/STATE.md` — sección UC-F06: estilos, ID en `result.fires`, navegación disponible | `[ ]` | Tras despliegue de grupos A y B |
| F-04 | Actualizar `docs/STATE.md` — sección UC-F06: columna de ID en grilla de episodios | `[ ]` | Tras despliegue de grupo C |
| F-05 | Actualizar `docs/product/casos-de-uso-y-estado.md` — estado de UC-F06 a "listo en producción" | `[ ]` | Tras despliegue completo y validación |

---

## Orden de ejecución

```
Grupo 0  ─── completo

Grupo A  ──┬── sin dependencias (ejecutar primero, en paralelo con B)
Grupo B  ──┤
Grupo B2 ──┤── depende de B-05 y B-06
Grupo B3 ──┘── depende de B2-03

PRE-C ───────── depende de B2-01 (tipo definido); desbloquea grupo C
Grupo C  ──────── depende de PRE-C

Grupo D  ──── D-01 a D-10: tras grupos A y B
             D-11 a D-14: tras grupo C

Grupo E  ──── tras grupos A, B y C
Grupo F  ──── F-01 a F-03: tras despliegue de A y B
             F-04 a F-05: tras despliegue de C y validación
```

---

*Documento generado: 2026-03-16*  
*Basado en: análisis crítico en tres rondas + hallazgos de Fase 1 + implementación de backend confirmada.*