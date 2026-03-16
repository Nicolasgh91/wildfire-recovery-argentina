# Tareas técnicas de implementación — UC-F06 (página de auditoría / verificar terreno)

> Generado tras análisis crítico en tres rondas y hallazgos de Fase 1.  
> Estado de fase 1: **completa**. Decisiones de fases 2 y 3: **fijadas** en este documento.  
> Archivo de entrada: `audit_update_plan.md` con tablas de hallazgos.

---

## Decisiones fijadas (no requieren confirmación adicional)

### D-01 — Color de botones y paginación

**Situación confirmada por Fase 1:**
- Los presets de área usan hoy `variant="default"` (seleccionado) y `variant="outline"` (no seleccionado).
- La paginación usa `variant="outline"`.
- No existe una variante de botón dedicada al verde legal; el verde se implementa con clases Tailwind directas en el resto de la app.

**Decisión:** usar la **opción A** (quirúrgica, sin crear variante nueva):
- Mantener `variant="outline"` como base para presets no seleccionados y paginación.
- Agregar clases Tailwind de verde sobre `outline`:
  `border-emerald-600 text-emerald-700 hover:bg-emerald-50 dark:border-emerald-500 dark:text-emerald-400`
- El preset seleccionado mantiene `variant="default"` (ya tiene el estilo correcto).

---

### D-02 — ID en la grilla de episodios

**Situación confirmada por Fase 1:**
- `AuditSearchEpisode` (grilla principal) **no expone `fire_event_id`**; solo tiene `episode.id`.
- `AuditFire` (lista de incendios puntuales en `result.fires`) **sí tiene `fire_event_id`**, usado hoy como `key` en la UI pero sin navegación.

**Decisión:**
- La columna de ID y la navegación clickeable se implementan **sobre `result.fires` / `AuditFire`** (donde existe `fire_event_id`), no sobre la grilla de episodios.
- La grilla de episodios **no recibe columna de ID** en esta iteración; el `episode.id` no es apto como ID legal.
- Se crea un item de backlog bloqueante para ampliar `/audit/search` y exponer `fire_event_id` por episodio en una iteración de backend futura.

---

### D-03 — Responsividad de la grilla

**Situación confirmada por Fase 1:**
- La tabla tiene 8 columnas hoy con `min-w-[980px]` y `overflow-x-auto`.
- La navegación clickeable se implementa sobre `result.fires` (tarjetas o lista), no sobre la tabla de episodios, por lo que **no se agrega ninguna columna nueva a la grilla de 8 columnas**.
- El riesgo de responsividad queda mitigado por decisión D-02.

---

### D-04 — `ReturnContext` para origen `audit`

**Situación confirmada por Fase 1:**
- No existe hoy origen `audit` en `ReturnContext`.
- El patrón existente es ligero: `home` guarda scroll; `history` guarda querystring; `map` guarda ID seleccionado.

**Decisión:** extender `ReturnContext` con:

```typescript
// En frontend/src/types/navigation.ts
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

Restricciones:
- **Nunca** guardar listas de resultados ni textos de búsqueda en `sessionStorage`.
- Solo parámetros compactos que reconstruyan la vista.

---

## Tareas de implementación

### Grupo A — Ajustes de UI (presets y paginación)
> Desbloqueado. No depende de backend ni de navegación.

---

#### A-01 — Presets de área: actualizar color de botones no seleccionados

**Archivo:** `frontend/src/pages/Audit.tsx`

**Qué hacer:**
1. Localizar el bloque que renderiza los `AREA_PRESETS` (3 botones de área de análisis).
2. Para los botones con `variant="outline"` (estado no seleccionado), agregar las clases:
   `border-emerald-600 text-emerald-700 hover:bg-emerald-50`
3. Confirmar que el botón seleccionado (`variant="default"` o condición `analysisPreset === opt.value`) **no recibe estas clases** — debe conservar su estilo actual.
4. Verificar accesibilidad: foco visible (`focus-visible:ring`), contraste suficiente en hover/active.

**Criterio de aceptación:**
- Los 3 botones de área muestran verde en estado no seleccionado.
- El botón seleccionado mantiene su diferenciación visual sin mezclar estilos.
- No se introducen bucles ni lógica nueva; solo ajuste de clases/props.

---

#### A-02 — Paginación de la grilla: actualizar color de botones

**Archivo:** `frontend/src/pages/Audit.tsx`

**Qué hacer:**
1. Localizar los botones "Anterior" y "Siguiente" de la tabla de episodios.
2. Agregar sobre `variant="outline"` las mismas clases verdes:
   `border-emerald-600 text-emerald-700 hover:bg-emerald-50`
3. Confirmar que el estado `disabled` (primera/última página) desactiva correctamente el color verde y aplica el estilo deshabilitado estándar (`opacity-50 cursor-not-allowed`).
4. Evaluar si conviene reemplazar la paginación inline por el componente `frontend/src/components/fires/pagination.tsx`:
   - Solo si la API del componente es compatible y la integración no requiere más de 15 líneas de cambio.
   - Si no, documentar en comentario inline por qué se mantiene la paginación propia.

**Criterio de aceptación:**
- Botones de paginación muestran verde consistente con los presets (A-01).
- El estado `disabled` no muestra verde (no se ve un botón verde deshabilitado sin feedback).
- El conteo "Mostrando X–Y de N" no cambia.

---

### Grupo B — ID visible y navegación clickeable en `result.fires`
> Desbloqueado. Depende de D-02 y D-04 (decisiones ya fijadas).

---

#### B-01 — Agregar ID de incendio visible en cada tarjeta/fila de `result.fires`

**Archivo:** `frontend/src/pages/Audit.tsx`

**Qué hacer:**
1. Localizar el bloque que renderiza `result.fires` (lista de `AuditFire`).
2. Para cada ítem, mostrar el `fire_event_id` truncado (primeros 8 caracteres + `...`) con tooltip del ID completo.
3. Etiquetar como "ID de incendio" con tipografía secundaria (`text-xs text-muted-foreground font-mono`).
4. Confirmar que el ID mostrado es exactamente el mismo que se usará en la tarea B-02 para navegar.

**Criterio de aceptación:**
- El ID visible coincide exactamente con el `fire_event_id` del registro.
- El tooltip muestra el ID completo al hacer hover.
- Si `fire_event_id` fuese `null` o vacío (caso borde): mostrar "N/D" y no renderizar el link de navegación (ver B-02).

---

#### B-02 — Hacer clickeable cada registro de `result.fires` con navegación a `/fires/:id`

**Archivo:** `frontend/src/pages/Audit.tsx`

**Qué hacer:**
1. Agregar un botón o link explícito (ícono `ExternalLink` o texto "Ver detalle") por cada ítem de `result.fires`.
2. Al hacer click, ejecutar:

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

3. Si `fire_event_id` está ausente o vacío: deshabilitar o no renderizar el link/botón.

**Criterio de aceptación:**
- El click navega a `/fires/:fire_event_id` correctamente.
- El `ReturnContext` en `sessionStorage` contiene solo: `returnTo`, `lat`, `lon`, `radius`, `page`. Sin listas de resultados.
- Cuando `fire_event_id` no está disponible, el botón no existe o está deshabilitado con tooltip explicativo.

---

#### B-03 — Extender `ReturnContext` y `handleBack` en `FireDetailPage`

**Archivos:**
- `frontend/src/types/navigation.ts`
- `frontend/src/pages/FireDetail.tsx`

**Qué hacer:**

En `navigation.ts`:
1. Agregar el tipo `AuditReturnContext` (ver D-04).
2. Incluirlo en el union type de `ReturnContext`.

En `FireDetail.tsx`:
1. En el handler `handleBack`, agregar el caso `returnTo === 'audit'`:

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

2. Verificar que `AuditPage` lee `location.state?.restore` para repoblar los filtros y la página al volver (si no lo hace hoy, agregar ese comportamiento en `Audit.tsx`).

**Criterio de aceptación:**
- Desde `/fires/:id` (originado en auditoría), el botón "Volver" regresa a `/audit` con los filtros y la página correctos.
- Los flujos existentes (`home`, `history`, `map`) no se ven afectados.

---

#### B-04 — Verificar guard de autenticación y limpieza de `ReturnContext`

**Archivos:**
- `frontend/src/pages/Audit.tsx`
- `frontend/src/pages/FireDetail.tsx`
- Guard de autenticación existente (ruta o contexto)

**Qué hacer:**
1. Confirmar que el guard que protege UC-F06 (`/audit`) también cubre el link de navegación a `/fires/:id` — el usuario no puede acceder al detalle si la sesión expiró.
2. Si la sesión expira entre la búsqueda y el click:
   - El guard de `/fires/:id` redirige a login (o al flujo estándar de re-autenticación).
   - Al redirigir, limpiar o no persistir el `ReturnContext` de auditoría para evitar un estado "volver a auditoría" inconsistente tras el login.
3. Verificar que no se navegue a `/fires/:id` con un contexto de auditoría si el guard determina sesión inválida.

**Criterio de aceptación:**
- Sesión válida: flujo completo funciona (auditoría → detalle → volver).
- Sesión expirada: redirección a login sin dejar `ReturnContext` de auditoría residual en `sessionStorage`.

---

### Grupo C — Testing

---

#### C-01 — Tests de UI para `AuditPage`

**Archivo:** `frontend/src/pages/__tests__/AuditPage.test.tsx` (crear si no existe)

**Casos a cubrir:**

| Caso | Verificación |
|------|-------------|
| Presets de área — estado no seleccionado | Los botones tienen clases `border-emerald-600 text-emerald-700` |
| Presets de área — estado seleccionado | El botón seleccionado **no** tiene las clases verdes de outline |
| Paginación — primera página | Botón "Anterior" tiene `disabled` |
| Paginación — última página | Botón "Siguiente" tiene `disabled` |
| Paginación — página intermedia | Ambos botones habilitados y con clases verdes |
| ID de incendio visible | El ID truncado mostrado coincide con `fire_event_id` del registro |
| ID ausente | Columna muestra "N/D"; link/botón de detalle ausente o deshabilitado |
| Navegación a detalle | `navigate` recibe `/fires/:fire_event_id` y el `ReturnContext` con `returnTo: 'audit'` |
| `sessionStorage` | Solo contiene `lat`, `lon`, `radius`, `page`; no contiene listas de resultados |

---

#### C-02 — Verificación manual de regresiones visuales

**Qué revisar:**
- `/audit` en desktop (≥ 1280px): presets y paginación con verde consistente.
- `/audit` en mobile (< 768px): la grilla de episodios no se rompe (sigue con scroll horizontal); la sección `result.fires` es legible con el ID truncado y el link de detalle.
- Temas claro y oscuro (si aplica): contraste suficiente del verde en ambos temas.
- Flujos existentes sin cambios: `/`, `/fires/history`, `/map` → `/fires/:id` → volver: ninguno afectado.

---

### Grupo D — Documentación y backlog

---

#### D-01-DOC — Registrar ADR de origen `audit` en `ReturnContext`

**Archivo:** `docs/decisions/adr.md`

**Qué documentar:**
- Decisión: se agrega origen `returnTo: 'audit'` al union type de `ReturnContext`.
- Campos permitidos: `lat`, `lon`, `radius`, `page`.
- Restricción: nunca guardar resultados de auditoría ni textos de búsqueda en `sessionStorage` (ley 25.326).
- Comportamiento de `FireDetail` al recibir origen `audit`: navegar a `/audit` con `state.restore`.

---

#### D-02-DOC — Backlog: ampliar `/audit/search` para exponer `fire_event_id` por episodio

**Archivo:** `docs/tasks/backlog.md`

**Ítem a registrar:**

```
[BLOQUEANTE para ID legal en grilla de episodios]
Ampliar respuesta de /audit/search para que AuditSearchEpisode exponga
fire_event_id (o representative_event_id) por episodio.
Motivo: la grilla de episodios de auditoría no puede mostrar un ID legal
ni ofrecer navegación a /fires/:id sin este campo.
Prerequisito para: columna de ID en grilla de episodios + navegación
clickeable desde esa grilla.
```

---

#### D-03-DOC — Actualizar estado de UC-F06

**Archivos:**
- `docs/STATE.md` (sección UC-F06)
- `docs/product/casos-de-uso-y-estado.md` (estado de UC-F06)

**Qué actualizar:**
- Estilos: presets de área y paginación con verde consistente (clases emerald sobre `outline`).
- ID visible: `fire_event_id` en la sección `result.fires`; grilla de episodios sin ID (pendiente de backend).
- Navegación: link explícito por incendio en `result.fires` → `/fires/:id` con `ReturnContext` de auditoría.
- Estado de UC-F06: actualizar de "en progreso" a "listo en producción" (o el estado que corresponda tras el despliegue).

---

## Resumen de dependencias y orden de ejecución

```
A-01  ──┐
A-02  ──┤── sin dependencias, ejecutar primero (paralelo)
        │
B-01  ──┤── depende de D-02 (decisión fijada: fire_event_id en result.fires)
B-02  ──┤── depende de D-04 (estructura de ReturnContext fijada)
B-03  ──┤── depende de B-02 (necesita el tipo AuditReturnContext definido)
B-04  ──┘── depende de B-02 y B-03

C-01  ──── depende de A-01, A-02, B-01, B-02
C-02  ──── depende de todos los grupos A y B

D-01-DOC ── paralelo (puede escribirse antes de implementar)
D-02-DOC ── paralelo
D-03-DOC ── última (tras despliegue confirmado)
```

---

## Roadmap

```
■ Fase 1 — Hallazgos (completa)
■ Fase 2/3 — Decisiones fijadas (en este documento)

▶ Grupo A — Presets y paginación (ejecutable ahora)
▶ Grupo B — ID + navegación en result.fires (ejecutable ahora)
○ Grupo C — Testing
○ Grupo D — Documentación y actualización de estado UC-F06

◇ Backend: ampliar /audit/search → fire_event_id en grilla de episodios
```

---

*Documento generado: 2026-03-16*  
*Basado en: `audit_update_plan.md` con hallazgos de Fase 1 + análisis crítico en tres rondas.*
