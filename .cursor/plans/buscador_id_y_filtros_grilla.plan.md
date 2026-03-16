---
name: ""
overview: ""
todos: []
isProject: false
---

# Plan: Buscador por ID y más filtros en grilla de históricos (v2)

## Objetivo

1. Permitir búsqueda por **ID completo** de evento en el buscador de la grilla.
2. Ampliar el **panel de filtros avanzados** con opciones alineadas a las columnas (departamento, área protegida, significativo, imágenes, confianza, detecciones), sin regresiones en KPIs ni en export.

---

## Reglas críticas (evitar regresiones)

### 1. Colisión `search` vs `department`

- **Problema:** El buscador `search` aplica ILIKE sobre provincia, departamento y nombre de área protegida. Si además hay filtro explícito `department`, el backend podría aplicar ambas condiciones y generar contradicción o duplicado.
- **Regla:** En `build_filter_conditions`, cuando `params.department` esté definido (no vacío), el bloque de búsqueda por texto **no** debe incluir la condición sobre departamento. Solo se aplica:
  - `FireEvent.department.ilike(...)` cuando **no** hay `params.department`.
  - Si hay `params.department`, se usa únicamente la condición explícita `FireEvent.department.ilike(f"%{params.department}%")` (ya existente en el bloque `if params.department`).
- **Resultado:** Sin condiciones duplicadas ni contradictorias; el filtro explícito `department` tiene precedencia para el campo departamento.

### 2. Validación UUID: mismo criterio en backend y frontend

- **Problema:** Si solo el frontend valida UUID y el backend acepta cualquier `search` con `len >= 2`, una cadena de 32 hex que el frontend no reconozca como UUID llegaría al backend y se usaría en ILIKE, dando resultados incorrectos.
- **Regla:**
  - **Backend (fuente de verdad):** En `build_filter_conditions`, antes del bloque de búsqueda por texto, detectar si `params.search` es un UUID válido (ver punto 7). Si lo es → filtrar solo por `FireEvent.id == <uuid_normalizado>` y **no** ejecutar el bloque ILIKE. Si no es UUID → aplicar solo el bloque ILIKE (respetando la regla de exclusión de departamento cuando `params.department` esté definido).
  - **API (`fires.py`):** Aceptar `search` cuando `len(search.strip()) >= 2` **o** cuando la cadena sea UUID válido (32 o 36 caracteres según criterio unificado). Así un ID completo siempre llega al servicio.
  - **Frontend:** Usar el **mismo** criterio de detección de UUID que el backend (helper reutilizable o documentado): si el input es UUID válido, enviar `search` aunque tenga longitud 32/36; si no, enviar solo si `length >= 2`. Objetivo: no enviar 32 hex “a ciegas” para evitar ILIKE sobre ese string.

### 3. `buildStatsParams`: mismos filtros que la grilla

- **Problema:** Si los KPIs no reciben los mismos filtros que la grilla, los números del dashboard no coinciden con la tabla (regresión UC-F03).
- **Regla:** `buildStatsParams` debe incluir **exactamente** los mismos filtros que `buildApiParams` (incluidos los 6 nuevos y `search`), mapeados a los query params que espera `GET /api/v1/fires/stats`. El endpoint de stats ya acepta `department`, `in_protected_area`, `is_significant`, `has_imagery`, `min_confidence`, `min_detections` y `search`; no hay ambigüedad: implementación obligatoria, no “decidir después”.
- **Deuda técnica explícita:** Si en el futuro se añade un filtro nuevo en la grilla que el endpoint de stats no soporte, se debe documentar en `tasks/tech_debt.md` y bloquear la exposición en UI de ese filtro hasta que stats lo soporte, o añadir el parámetro en el backend.

### 4. Booleanos en URL: serialización y casteo explícitos

- **Problema:** `in_protected_area`, `is_significant`, `has_imagery` en URL pueden ser `"true"`, `"false"`, `"all"` o ausentes. Si `parseFilters` lee un string y no castea a boolean, comparaciones como `filters.in_protected_area === true` fallan.
- **Regla:**
  - **Representación en URL:** Valores permitidos: ausente (o clave no presente) = “todos”; `"true"` = sí; `"false"` = no. No usar `"all"` en la URL; “todos” = omitir el parámetro.
  - **parseFilters:** Para cada uno de los tres campos, leer string y mapear: `''` / `undefined` / clave ausente → valor por defecto “sin filtrar” (ej. `undefined` o `null` en estado, según diseño). `"true"` → `true`, `"false"` → `false`. Cualquier otro valor → tratar como “sin filtrar”.
  - **buildSearchParams / buildApiParams:** Solo añadir el query param cuando el valor sea estrictamente `true` o `false`; si es “sin filtrar”, no escribir la clave (el API interpreta `Optional[bool] = None`).
  - Documentar en comentario o tipo el contrato: `FireFiltersState.in_protected_area?: boolean | null` (y análogo para los otros dos), y en API solo enviar cuando sea boolean.

---

## Schema y filtros derivados (no columnas directas)

### `has_imagery` e `in_protected_area` no son columnas en `fire_events`

- En `prod_schema.sql`, **no** existen columnas `has_imagery` ni `in_protected_area` en la tabla `fire_events`. El backend ya implementa ambos filtros así:
  - **has_imagery:** subquery/EXISTS sobre `satellite_images` donde `satellite_images.fire_event_id = fire_events.id` (ver `build_filter_conditions` en `fire_service.py`).
  - **in_protected_area:** EXISTS sobre `fire_protected_area_intersections` donde `fire_event_id = fire_events.id`.
- **Riesgo:** El agente podría asumir que son columnas directas y tocar el modelo o el schema por error. No hay que añadir columnas; la implementación actual es correcta.
- **Acción en FASE 1:** Verificar en `build_filter_conditions` que la implementación de `has_imagery` e `in_protected_area` sigue siendo por join/subquery/EXISTS. Confirmar que los índices relevantes están en **las tablas relacionadas**: `satellite_images.fire_event_id` y `fire_protected_area_intersections.fire_event_id`, no en `fire_events`. Si faltan índices en esas FKs, añadirlos o registrarlos en tech_debt antes de exponer los filtros en la UI.

---

## Performance

### 5. Índices para `min_confidence` y `min_detections`

- Los filtros usan **columnas directas** `FireEvent.avg_confidence` y `FireEvent.total_detections` (nombres correctos en `fire_events`). Antes de habilitar la UI, **verificar** si existen índices adecuados en `fire_events(avg_confidence)` y `fire_events(total_detections)` para evitar seq scans costosos con mucho volumen.
- **Tarea explícita en el plan:** Comprobar en el esquema/migraciones; si no existen, añadir `CREATE INDEX` (o tarea en backlog) como parte de esta feature o como ítem de tech_debt con prioridad definida.

### 6. Debounce en inputs del panel avanzado

- Para no re-renderizar la grilla en cada tecla al tipear en `department`, `min_confidence` o `min_detections`, aplicar **debounce** (por ejemplo 300–400 ms) antes de actualizar el estado que dispara la query. Reutilizar patrón existente del proyecto (ej. `useDebouncedValue` o similar para el buscador) en estos tres controles.

---

## Mejoras incluidas

### 7. UUID con y sin guiones (32 / 36 caracteres)

- **Criterio unificado (backend y frontend):** Considerar UUID válido si la cadena cumple:
  - Formato estándar 36 caracteres: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` (hex + guiones), o
  - Formato 32 caracteres hex: solo `[0-9a-fA-F]{32}`.
- **Normalización:** En backend, antes de comparar con `FireEvent.id`, normalizar el input a UUID con guiones (por ejemplo insertar guiones en posiciones 8, 12, 16, 20 si se reciben 32 hex). Así tanto búsqueda con guiones como sin guiones hacen match contra la columna UUID. Documentar en el plan que la comparación en BD se hace con el UUID normalizado.

### 8. Export CSV y límite sync/async

- La lógica actual de export (síncrono <1000, asíncrono >1000) se mantiene. Los nuevos filtros forman parte de `buildExportParams`; el total de registros que se exporta es el mismo que el que cumple los filtros de la grilla. Dejar explícito en el plan que la regla de sync/async se aplica **después** de aplicar todos los filtros (incluidos los 6 nuevos), para que no quede ambigüedad si el usuario filtra fuerte y espera descarga inmediata.

### 9. `hasActiveFilters` por comparación con `DEFAULT_FILTERS`

- En lugar de una lista manual de campos (“tiene province o date_from o …”), implementar **comparación estructural** del estado actual de filtros contra `DEFAULT_FILTERS` (todos los campos que participan en filtrado, incluidos los 6 nuevos). Así, cualquier campo nuevo que se agregue a `DEFAULT_FILTERS` queda automáticamente considerado para mostrar “Limpiar filtros” y evitar olvidar campos (evitar bugs de mantenimiento).

---

## Roadmap de implementación

```
FASE 1 — Backend (sin cambios de schema)
├── build_filter_conditions (fire_service.py):
│   ├── Detección UUID unificada (32/36 chars + normalización a formato con guiones).
│   ├── Si search es UUID → filtro FireEvent.id solo; no aplicar bloque ILIKE.
│   └── Si params.department está definido → no incluir departamento en el bloque ILIKE de search.
├── fires.py (list_fires, get_statistics, export): aceptar search si len>=2 O si es UUID válido.
├── Verificar implementación de has_imagery e in_protected_area: no son columnas en fire_events; se implementan con EXISTS/subquery (satellite_images.fire_event_id, fire_protected_area_intersections.fire_event_id). Confirmar que los índices relevantes están en esas tablas relacionadas, no en fire_events.
└── Verificar índices: fire_events(avg_confidence), fire_events(total_detections); satellite_images(fire_event_id); fire_protected_area_intersections(fire_event_id). Añadir si faltan.

FASE 2 — Tipos y contratos
├── fire.ts: extender FireFiltersState con department, in_protected_area, is_significant, has_imagery, min_confidence, min_detections.
├── Definir contrato de booleanos: valor en estado (boolean | null/undefined), en URL solo "true"/"false" o ausente.
└── DEFAULT_FILTERS en FireHistory.tsx con todos los campos (incluidos los 6 nuevos).

FASE 3 — FireHistory.tsx
├── parseFilters: leer los 6 campos de URL; casteo explícito de "true"/"false" → boolean para los 3 booleanos.
├── buildSearchParams: serializar los 6 filtros; booleanos solo cuando true/false.
├── buildApiParams: mismos filtros + mapeo correcto de booleanos (solo enviar si true/false).
├── buildStatsParams: mismos filtros que buildApiParams (sin excepción).
├── buildExportParams: mismos filtros que buildApiParams.
├── Helper isValidUuid (32/36 chars, mismo criterio que backend); enviar search si len>=2 o isValidUuid(search).
├── hasActiveFilters: comparación contra DEFAULT_FILTERS (no lista manual).
└── Carga de filtros guardados (user_saved_filters.filter_config): al aplicar un filtro guardado, hacer **merge con DEFAULT_FILTERS** para rellenar campos faltantes. Los filtros guardados antes de esta feature no tendrán los 6 nuevos campos en filter_config; si se cargan sin merge, esos campos quedarían undefined y podrían romper buildApiParams o la UI. Una línea de merge (ej. { ...DEFAULT_FILTERS, ...loadedConfig }) asegura que siempre se disponga de valores por defecto para todos los campos.

FASE 4 — fire-filters.tsx
├── Placeholder del buscador: "Buscar por ubicación o ID de evento".
├── Panel avanzado: department (texto), in_protected_area, is_significant, has_imagery (select Todos/Sí/No), min_confidence, min_detections (numéricos).
├── Debounce en department, min_confidence, min_detections antes de onFiltersChange.
├── hasActiveFilters usando comparación con DEFAULT_FILTERS (o función que reciba defaults y state).
└── handleReset: reiniciar todos los campos a DEFAULT_FILTERS.

FASE 5 — Verificación
├── Test: UUID completo (36 y 32 chars) → 1 resultado cuando existe.
├── Test: UUID inexistente → 0 resultados.
├── Test: department activo + search con texto → sin condición duplicada sobre departamento; resultados correctos.
├── Test: KPIs (stats) y grilla con mismos filtros → números consistentes.
├── Test: "Limpiar filtros" reinicia los 6 nuevos campos.
└── Test: Export CSV con filtros activos; regla sync/async aplicada sobre resultado filtrado.
```

---

## Archivos a tocar (resumen)


| Área     | Archivo                                          | Cambios principales                                                                                                                                                                                                                                                  |
| -------- | ------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Backend  | `app/services/fire_service.py`                   | UUID en search → filtro por id; exclusión de depto en ILIKE cuando hay `params.department`; normalización UUID 32→36.                                                                                                                                                |
| Backend  | `app/api/v1/fires.py`                            | Aceptar `search` cuando sea UUID válido (además de len>=2). Aplicar mismo criterio en list_fires, get_statistics y export.                                                                                                                                           |
| Backend  | Schema/DB                                        | Verificar índices: `fire_events(avg_confidence, total_detections)`; `satellite_images(fire_event_id)`; `fire_protected_area_intersections(fire_event_id)`. No añadir columnas `has_imagery`/`in_protected_area` en fire_events.                                      |
| Frontend | `frontend/src/types/fire.ts`                     | FireFiltersState + FireFilters con los 6 campos; contrato boolean opcional.                                                                                                                                                                                          |
| Frontend | `frontend/src/pages/FireHistory.tsx`             | DEFAULT_FILTERS completo; parseFilters (con casteo boolean); buildSearchParams, buildApiParams, buildStatsParams, buildExportParams alineados; isValidUuid; hasActiveFilters vs DEFAULT_FILTERS; al cargar filtro guardado: merge filter_config con DEFAULT_FILTERS. |
| Frontend | `frontend/src/components/fires/fire-filters.tsx` | Placeholder; panel avanzado con 6 controles; debounce en department y numéricos; reset y hasActiveFilters.                                                                                                                                                           |


---

## Criterios de aceptación (recordatorio)

- Buscar por ID completo (con o sin guiones) muestra ese evento o vacío.
- Búsqueda por texto (ubicación) sin filtro department sigue igual; con filtro department no hay doble condición sobre departamento.
- KPIs y grilla comparten los mismos filtros (buildStatsParams = buildApiParams en conjunto de filtros).
- Booleanos en URL con representación única; parseFilters y build*Params consistentes.
- "Limpiar filtros" deja todos los filtros (incluidos los 6 nuevos) en DEFAULT_FILTERS.
- Export CSV respeta todos los filtros; sync/async según total filtrado.
- Filtros guardados (user_saved_filters) cargados con merge a DEFAULT_FILTERS para que configs antiguos tengan valores por defecto en los 6 nuevos campos.

