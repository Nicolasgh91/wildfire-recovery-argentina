### Plan UC-F06 – Página de auditoría / verificar terreno

Este plan incluye las correcciones de la segunda revisión crítica.

---

### Fase 1 – Hallazgos bloqueantes (solo lectura, sin cambios)

**Objetivo:** producir hallazgos que destraben decisiones posteriores, incluyendo impacto en responsividad.

- **1.1. Inspección de UC-F06 (código de auditoría)**  
  - Revisar `frontend/src/pages/Audit.tsx`, `frontend/src/types/audit-search.ts` y `frontend/src/types/audit.ts` para responder por escrito:
    - Qué IDs hay por estructura: `AuditSearchEpisode.id`, `AuditFire.fire_event_id`, otros.  
    - Si la grilla principal de auditoría (episodios) tiene acceso directo o indirecto a un `fire_event_id`.

- **1.2. Inspección del sistema de diseño (colores y variantes)**  
  - Revisar `Button.tsx` (o equivalente) y los tokens/tema (ej. `theme.ts`, `tailwind.config`, etc.) para:
    - Listar variantes reales (`primary`, `secondary`, `outline`, `ghost`, `brand`, etc.).  
    - Identificar cuál es la variante que corresponde al **verde legal** usado como referencia (no asumir que es `secondary`).

- **1.3. Inspección de navegación y `ReturnContext`**  
  - Revisar:
    - `frontend/src/pages/FireHistory.tsx`  
    - `frontend/src/components/fires/fire-card.tsx`  
    - `frontend/src/components/map/layers/FireMarkers.tsx`  
    - `frontend/src/components/map/layers/EpisodeLayer.tsx`  
    - `frontend/src/pages/FireDetail.tsx`  
    - `frontend/src/types/navigation.ts`  
    - `frontend/src/lib/routing.ts`  
  - Para:
    - Mapear orígenes actuales (`home`, `history`, `map`), estructura de `ReturnContext` y contenido de `sessionStorage`.  
    - Verificar si ya existe origen `audit` o si hay que introducirlo.  
    - Ver qué datos exactos se persisten (asegurar que no sean sensibles).

- **1.4. Riesgos de responsividad al agregar columna de ID**  
  - Analizar la grilla actual de resultados de auditoría:
    - ¿Cuántas columnas tiene hoy en desktop y en mobile?  
    - ¿Cómo se comporta en resoluciones pequeñas (breakpoints)?  
    - ¿Hay espacio visual razonable para una columna adicional de ID en mobile?  
      - Si no lo hay, anotar alternativas: columna visible solo en desktop, tooltip con ID, truncado, etc.

**Output de Fase 1 (documento de hallazgos):**

- Tabla 1: **IDs disponibles** (estructura → campos → propósito → apto como ID legal sí/no).  
- Tabla 2: **Variantes de botón** (nombre → color real → usos actuales → ¿equivalente al verde legal?).  
- Tabla 3: **Orígenes de navegación** (origen → cómo arma `ReturnContext` → qué guarda en `sessionStorage`).  
- Tabla 4: **Riesgos de responsividad** (breakpoint → nº de columnas visibles → riesgo de agregar ID → recomendación).

Ninguna fase posterior se considera desbloqueada hasta tener este output.

---

### Fase 2 – Decisiones de diseño (color y semántica de ID) – bloqueada por Fase 1

**Objetivo:** fijar decisiones antes de tocar UI.

- **2.1. Decisión de color de botones/paginación**  
  - Con base en los hallazgos de Fase 1:
    - Elegir explícitamente la variante que corresponde al verde deseado (ej.: `secondary`, `brand`, `forest`, etc.).  
    - Documentar: “Los presets de área de análisis y la paginación de la grilla de auditoría usarán la variante `<VARIANTE_ELEGIDA>`”.

- **2.2. Decisión de ID visible (alineado a UC-F06 y ley 26.815)**  
  - A partir de los tipos inspeccionados:
    - Priorizar **`fire_event_id`** como ID de incendio relevante para la evidencia legal.  
    - Si la grilla de episodios solo tiene `episode.id`:
      - Definir si se mostrará como “ID de episodio” (semántica técnica explícita) o si solo se expondrá `fire_event_id` en la sección `result.fires`.  
    - Si el ID de incendio necesario no está disponible en la grilla:
      - Crear item **bloqueante** de backend para exponerlo en `/audit/search` (en `docs/tasks/backlog.md`), marcándolo como prerrequisito para la solución completa.

---

### Fase 3 – ADR de navegación / ReturnContext – bloqueada por Fase 1

**Objetivo:** fijar la decisión arquitectónica antes de implementar navegación desde auditoría.

- Definir en `docs/decisions/adr.md` (nuevo registro o ampliación):
  - Incorporación de un nuevo origen `returnTo: 'audit'`, con:
    - Campos mínimos (filtros compactos, número de página).  
    - Restricción explícita de no guardar listas de resultados ni datos sensibles de auditoría en `sessionStorage`.
  - Cómo debe comportarse `FireDetail` al recibir un `ReturnContext` con origen `audit`:
    - Comportamiento del botón de “Volver”.  
    - Qué ocurre si la sesión expiró entre la búsqueda en auditoría y el click al detalle:
      - **No** acceder a `/fires/:id` con un `ReturnContext` de auditoría si el guard de autenticación determina que la sesión ya no es válida.  
      - Redirigir a login o al flujo estándar definido, sin dejar residuos inconsistentes de `ReturnContext`.

---

### Fase 4 – Ajustes de UI independientes de datos (presets de área y paginación)

**Desbloqueada tras Fase 2 (variante de color decidida).**

- **4.1. Presets de área de análisis (tarjeta de búsqueda)**  
  - En `Audit.tsx`:
    - Cambiar la variante de los 3 botones de `AREA_PRESETS` de la variante legacy (`outline` u otra) a la variante acordada (`<VARIANTE_ELEGIDA>`).  
    - Mantener el estado de selección con lógica explícita (`analysisPreset === preset.value`) y estilos acordes.  
    - Revisar accesibilidad: foco visible, contraste suficiente, estados hover/active claros.

- **4.2. Paginación de grilla de resultados**  
  - En `Audit.tsx`:
    - Actualizar botones “Anterior” / “Siguiente” a la misma variante `<VARIANTE_ELEGIDA>`.  
    - Confirmar que `disabled` está correctamente aplicado en primera/última página.  
  - Evaluar si integrar el componente `Pagination` genérico (`frontend/src/components/fires/pagination.tsx`):
    - Solo si la integración es simple y reduce duplicación sin romper comportamientos existentes; si no, mantener la paginación inline pero estilísticamente alineada.

---

### Fase 5 – ID en grilla y política de ausencia de ID – bloqueada por Fase 1 y 2

**Objetivo:** exponer un identificador útil y coherente con el flujo legal, sin incoherencias visuales.

- **5.1. Columna de ID (si hay ID apto)**  
  - Si para cada fila se dispone de un `fire_event_id` o equivalente:
    - Agregar una columna en la grilla (posición a definir: p.ej. primera o penúltima) con etiqueta clara (“ID de incendio”).  
    - Asegurar que el ID mostrado sea el mismo que luego se use para navegar a `/fires/:id`.

- **5.2. Estrategia cuando solo hay `episode.id`**  
  - Si únicamente existe `episode.id` en `AuditSearchEpisode`:
    - Decidir si se expone como “ID de episodio” para referencia técnica, o si se omite como ID legal.  
    - Si se necesita sí o sí un ID de incendio para auditar, documentar que la solución completa depende de la ampliación de `/audit/search` (item de backend bloqueante).

- **5.3. Política de filas sin ID navegable (coherencia visual)**  
  - Definir comportamiento claro:
    - Si no hay `fire_event_id` para una fila/registro:
      - El link/botón de “ver detalle” se deshabilita o no se renderiza.  
      - La columna de ID debe estar **vacía o marcada como “N/D”** (no disponible), de forma consistente con la ausencia del link.  
      - Evitar el estado “ID visible pero link no clickeable sin explicación”.

---

### Fase 6 – Navegación clickeable a detalle de incendio – bloqueada por Fase 3 y 5

**Objetivo:** permitir ir a `/fires/:id` desde auditoría sin romper flujos, autenticación ni protección de datos.

- **6.1. Punto clickable por registro**  
  - Implementar **un icono o link explícito** (no la fila completa) para ir al detalle:
    - En la grilla de episodios, si hay ID adecuado, o  
    - En los bloques de `result.fires`, donde existe `fire_event_id`.

- **6.2. Construcción de navegación**  
  - En `Audit.tsx`:
    - Construir un `ReturnContext` con origen `audit` según ADR: filtros compactos + página.  
    - Guardarlo en `sessionStorage` (`RETURN_CONTEXT_KEY`) y pasar también en `state` a `navigate`.  
    - Navegar a `/fires/:id` usando `fire_event_id` (o el ID definido en Fase 5).

- **6.3. Casos borde de autenticación (reformulado)**  
  - En lugar de asumir usuarios no autenticados en auditoría, verificar:
    - Que el **guard de autenticación** que protege UC-F06 cubre también el flujo del link de navegación.  
    - Que, si la sesión expiró entre la búsqueda y el click:
      - El acceso a `/fires/:id` con `ReturnContext` de auditoría no se permite sin re-autenticación.  
      - La redirección a login (o flujo que corresponda) limpia o normaliza el `ReturnContext` para no dejar un estado imposible de “volver a auditoría”.

---

### Fase 7 – Testing, integridad referencial, performance y protección de datos

**Objetivo:** demostrar corrección y cumplimiento legal, no solo funcionamiento aparente.

- **7.1. Tests de UI y navegación para `AuditPage` (incluyendo casos negativos)**  
  - Tests (ej. `frontend/src/pages/__tests__/AuditPage.test.tsx`):
    - Presets de área: render, color esperado según `<VARIANTE_ELEGIDA>`, estado seleccionado.  
    - Paginación: estados `disabled` en bordes, conteo “Mostrando X–Y de N”.  
    - Columna de ID:
      - Caso positivo: el valor mostrado coincide exactamente con el ID usado en la navegación al hacer click en el link/botón.  
      - Caso negativo: cuando el link está deshabilitado o ausente (por falta de ID apto), la columna de ID también está vacía o marcada como “N/D”, y no existe un ID visible sin acción asociada.
    - Link/botón de detalle:
      - Navega a `/fires/:id` con el `ReturnContext` esperado cuando hay ID apto.  
      - No se renderiza o no es clickeable cuando la política de Fase 5.3 lo indica.

- **7.2. Verificación de `sessionStorage` y ley 25.326**  
  - Asegurar que:
    - Solo se guardan datos mínimos (origen, filtros compactos, página).  
    - No se persisten textos completos de búsqueda ni resultados, ni otros datos sensibles de auditoría.

- **7.3. Revisión de performance y responsividad**  
  - Confirmar que:
    - Solo se añade una columna y algunos links/botones, sin cambiar el volumen de datos de `/audit/search`.  
    - En mobile, el agregado de la columna de ID no rompe la grilla:
      - Si Fase 1 determinó riesgo, validar que se aplica la estrategia acordada (columna solo en desktop, tooltip, truncado, etc.).

---

### Fase 8 – Documentación, roadmap y backlog

**Objetivo:** alinear cambios con la estructura de docs y el roadmap del proyecto.

- **8.1. Actualizar `docs/STATE.md` y el estado de UC-F06**  
  - En `docs/STATE.md`:
    - Describir brevemente:
      - Estilos actualizados (verde consistente en presets y paginación).  
      - Exposición de ID (episodio/incendio) según decisión final.  
      - Navegación disponible desde auditoría hacia detalle de incendio y comportamiento de “Volver”.  
    - Actualizar el estado de **UC-F06 verificar terreno** (por ejemplo, de “en progreso” a “listo en producción” si corresponde).  
  - Actualizar también el documento de estado/roadmap interno donde UC-F06 figure como “en progreso” (ej. `docs/product/casos-de-uso-y-estado.md` o equivalente) para reflejar el nuevo estado real.

- **8.2. Backlog y decisiones**  
  - `docs/tasks/backlog.md`:
    - Ampliación de `/audit/search` si se requiere exponer `fire_event_id` en la grilla.  
    - Cualquier mejora pendiente identificada en Fase 1 (por ejemplo, refinamientos de responsividad).  
  - `docs/decisions/adr.md`:
    - ADR sobre origen `audit` en `ReturnContext` y límites de datos en `sessionStorage`.  
    - Registrar, si aplica, la decisión de diseño sobre la visibilidad del ID en mobile (mostrar/ocultar/tooltip).

---

### Hallazgos Fase 1 – UC-F06 (bloqueantes)

#### Tabla 1 – IDs disponibles y aptitud legal

| Estructura / contexto                                   | Campo ID                       | Propósito / significado                                      | Usado hoy en UI                                             | ¿Apto como ID legal (evento incendio)? |
|---------------------------------------------------------|--------------------------------|--------------------------------------------------------------|-------------------------------------------------------------|----------------------------------------|
| `AuditSearchEpisode` (`frontend/src/types/audit-search.ts`) | `id: string`                   | Identificador de **episodio** en el contexto de búsqueda de auditoría. No expone relación directa con `fire_event_id`. | Clave de fila en la grilla de episodios de `AuditPage` (`TableRow key={episode.id}`). No se muestra como columna. | **No claro**. Es ID técnico de episodio; no está documentado como ID de evento legal. |
| `AuditFire` (`frontend/src/types/audit.ts`)             | `fire_event_id: string`        | Identificador de **evento/incendio** usado en el módulo de auditoría puntual (respuesta de `/audit`). | Se usa como `key={fire.fire_event_id}` en la lista de incendios puntuales dentro de `AuditPage`. No se navega hoy a `/fires/:id` desde acá. | **Sí, prioritario.** Es el ID natural para mapear al detalle `/fires/:id`. |
| `EvidenceThumbnail` (`frontend/src/types/audit.ts`)     | `fire_event_id: string`        | Referencia al mismo evento de incendio asociado a cada thumbnail satelital. | Parte de la clave de `Card` en `renderThumbnails` (`key=\`${thumb.fire_event_id}-${thumb.thumbnail_url}\``). | **Sí**, pero indirecto (soporte para navegación desde galería si se quisiera). |
| `FireRowDto` / `fires` en historial (`FireHistoryPage`) | `id: string`                   | ID del incendio en `/fires/history`. Se usa para navegar a `/fires/:id`. | Fila clickeable (`/fires/${row.id}`) y tooltip de ID truncado. | **Sí.** Este ID ya se usa como ID legal de incendio en el historial. |
| `Episode` en `EpisodeLayer` (mapa)                      | `id: string`                   | ID de episodio en la capa de mapa.                           | Usado para construir popup y `detailsHref` a `/fires/:id` vía `representative_event_id ?? id`. | **Condicional.** Sirve como fallback cuando no hay `representative_event_id`. |
| `Episode` en `EpisodeLayer` (mapa)                      | `representative_event_id?: string \| null` | ID de evento representativo para el episodio.                | Usado para `detailsHref = /fires/${encodeURIComponent(detailId)}` donde `detailId = representative_event_id ?? id`. | **Sí, preferible** cuando está presente. |
| `FireMapItem` en `FireMarkers`                          | `id: string` y `representative_event_id?: string \| null` (en backend/mapper) | ID de incendio en mapa.                                      | `detailId = fire.representative_event_id ?? fire.id` para navegar a `/fires/:id`. | **Sí.** Ya se usa como ID legal para navegación desde mapa. |

**Conclusión:**  
- El único ID inequívocamente apto para uso legal en UC-F06 es **`fire_event_id`** (en `AuditFire` y `EvidenceThumbnail`) y el **`id`** de incendios ya usado en historial/mapa.  
- La grilla de episodios de auditoría (`AuditSearchEpisode`) **no expone hoy ningún `fire_event_id`**, solo `episode.id`, por lo que **no se puede garantizar integridad legal sin ampliar el API** si se quiere navegar o mostrar un ID de incendio desde esa grilla.

---

#### Tabla 2 – Variantes de botón y colores disponibles

Fuente principal: `frontend/src/components/ui/button.tsx`.

| Variante `Button`        | Clase base / estilo principal                                                                                                      | Color semántico aparente                  | Usos relevantes observados                                      | ¿Coincide con “verde legal” actual? |
|--------------------------|-------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------|------------------------------------------------------------------|--------------------------------------|
| `default`                | `bg-primary text-primary-foreground hover:bg-primary/90`                                                                           | Depende de `primary` en tema              | Presets de área seleccionados en `AuditPage` (`analysisPreset === opt.value ? 'default'`) | **Depende de tema** (no confirmable sin tokens). |
| `secondary`              | `bg-secondary text-secondary-foreground hover:bg-secondary/80`                                                                     | Depende de `secondary` en tema            | Botones secundarios en varias vistas (ej. `FireCard` footer `variant="secondary"`). | **No confirmado.** Puede ser verde o gris según `secondary`. |
| `outline`                | `border bg-background shadow-xs hover:bg-accent hover:text-accent-foreground ...`                                                 | Borde neutro, fondo claro, hover `accent` | Presets de área no seleccionados en `AuditPage`; paginación de auditoría; múltiples botones “outline” en toda la app. | **No**: es estilo neutro, no el verde legal. |
| `destructive`            | `bg-destructive text-white hover:bg-destructive/90 ...`                                                                            | Rojo / error                              | Alertas, estados críticos, badges de severidad alta en algunas vistas. | No aplica. |
| `ghost`                  | `hover:bg-accent hover:text-accent-foreground ...`                                                                                | Transparente / hover `accent`             | Algunos icon buttons.                                            | No se usa como verde legal principal. |
| `link`                   | `text-primary underline-offset-4 hover:underline`                                                                                  | Texto primario                            | Links de texto.                                                  | No aplica. |

Observaciones adicionales:

- El **“verde legal”** visible en varias vistas (por ejemplo, badges de recuperación, elementos del mapa, tarjetas de historial) se implementa **con clases Tailwind directas** (`bg-emerald-100`, `text-emerald-700`, etc.), no con una variante dedicada de `Button`.  
- En `AuditPage`, los presets de área usan hoy:  
  - `variant="default"` para el preset seleccionado.  
  - `variant="outline"` para los no seleccionados.  
- En la paginación de auditoría, los botones “Anterior” / “Siguiente” usan `variant="outline"`, es decir, **no comparten el mismo color semántico** que el resto de CTAs verdes del producto.

**Conclusión:**  
- No existe hoy una variante de botón claramente etiquetada como “verde legal”; el verde se consigue con utilidades Tailwind sobre otros componentes.  
- La hipótesis de usar directamente `variant="secondary"` para el verde debe validarse primero contra el diseño visual (tokens de tema), o alternativamente crearse un patrón explícito (por ejemplo, clases Tailwind o una nueva variante) si `secondary` no es verde.

---

#### Tabla 3 – Orígenes de navegación (`ReturnContext`) y `sessionStorage`

Fuente principal: `frontend/src/types/navigation.ts`, `FireHistoryPage`, `FireCard`, `FireMarkers`, `FireDetailPage`.

| Origen (`returnTo`) | Dónde se genera                                     | Qué guarda en `ReturnContext` / `sessionStorage`                                     | Cómo se consume en `FireDetailPage`                         | Notas de seguridad / datos |
|---------------------|-----------------------------------------------------|--------------------------------------------------------------------------------------|-------------------------------------------------------------|----------------------------|
| `home`              | `FireCard` (`frontend/src/components/fires/fire-card.tsx`) | `{ returnTo: 'home', home: { scrollY } }` en `sessionStorage` (`RETURN_CONTEXT_KEY`). | `handleBack` detecta `returnTo === 'home'` y navega a `HOME_PATH` con `state.restore.scrollY`. | Solo persiste posición de scroll (no datos sensibles). |
| `history`           | `FireHistoryPage` (`FireRow.handleRowClick`)       | `{ returnTo: 'history', history: { search, scrollY } }` donde `search = location.search`. | `handleBack` navega a `/fires/history${search}`.            | Persiste únicamente querystring de filtros y scroll; no payloads. |
| `map`               | `FireMarkers` (popup botón “Ver detalles”)         | `{ returnTo: 'map', map: { selectedFireId: fire.id } }` en `sessionStorage`.         | `handleBack` navega a `/map` con `state.restore.selectedFireId`. | Solo guarda ID de incendio para re-seleccionar en mapa. |

Comportamiento general:

- `ReturnContext` se pasa por `location.state` y, como respaldo, se guarda en `sessionStorage` (`RETURN_CONTEXT_KEY = 'fg:return_context'`).  
- `FireDetailPage` intenta primero leer `location.state` y, si no hay contexto, intenta leer y luego **eliminar** (`removeItem`) el contexto de `sessionStorage`.  
- **No existe hoy un origen `audit`**, por lo que la navegación propuesta desde auditoría requerirá **extender `ReturnContext`** y el `handleBack`.

**Conclusión:**  
- El patrón actual de `ReturnContext` es **ligero y respetuoso de datos**: solo guarda scroll, filtros en querystring o IDs simples.  
- La extensión a `audit` debe seguir este patrón: **nunca guardar resultados completos de auditoría ni textos de búsqueda largos en `sessionStorage`**; solo parámetros compactos que permitan reconstruir la vista.

---

#### Tabla 4 – Riesgos de responsividad al agregar columna de ID en la grilla de auditoría

Fuente principal: sección de resultados de `AuditPage` (`frontend/src/pages/Audit.tsx`).

| Breakpoint / layout                          | Configuración actual de columnas                                             | Comportamiento actual con overflow                             | Riesgo al agregar columna de ID                               | Recomendación inicial |
|---------------------------------------------|------------------------------------------------------------------------------|----------------------------------------------------------------|---------------------------------------------------------------|-----------------------|
| Desktop (`lg` y superiores)                 | Tabla con **8 columnas**: Fecha, Estado, Provincia, Duración (días), FRP máx, Área (ha), Detecciones, Señal de recuperación. | Contenedor con `overflow-x-auto` y `Table` con `className="min-w-[980px]"`, permitiendo scroll horizontal cuando falta espacio. | **Bajo–medio**: una 9.ª columna (ID) incrementa el ancho mínimo, aumentando el scroll horizontal pero sin romper layout (ya preparado para scroll). | Aceptable siempre que la nueva columna use ancho contenido (ID truncado + tooltip). |
| Mobile / pantallas angostas (`< lg`)        | Misma tabla envuelta en contenedor con `overflow-x-auto`; en la práctica, el usuario debe hacer scroll horizontal para ver todas las columnas. | El usuario ya necesita scroll horizontal para consumir la tabla completa. | **Bajo**: la experiencia ya depende de scroll lateral; una columna extra no rompe el layout, pero puede hacer la tabla menos legible. | Considerar ocultar la columna de ID en mobile o mostrarla truncada con tooltip. |

Detalle técnico relevante:

- La tabla se declara como:
  - Contenedor: `<div className="w-full overflow-x-auto rounded-md border">`.  
  - Tabla: `<Table className="min-w-[980px]">`.  
- No hay lógica condicional por breakpoint dentro de la tabla; la responsividad se basa exclusivamente en scroll horizontal.

**Conclusión:**  
- Es técnicamente seguro agregar una columna de ID **desde el punto de vista de layout** (no rompe la página), pero puede degradar algo la experiencia en pantallas pequeñas.  
- La decisión de mostrar/ocultar el ID por breakpoint (o usar truncado/tooltip) deberá tomarse en Fase 2 y aplicarse en implementación (Fases 4–5), usando estos hallazgos como base.
