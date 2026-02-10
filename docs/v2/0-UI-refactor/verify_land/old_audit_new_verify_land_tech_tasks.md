# Prompt técnico para CODEX: rediseño UX/UI de “Auditoría” a “Verificar terreno”

## Objetivo
Transformar la página actual “Auditoría de uso del suelo” en una experiencia de **verificación de terreno** para público no técnico. Debe invitar a investigar incendios históricos y evolución vegetativa, con enfoque de curiosidad guiada (sin afirmar intencionalidad). El CTA principal debe ser **“Verificá”**.

## Alcance
Modificar la página existente (ruta actual de auditoría) y su navegación/labels asociados. Implementar mejoras de copy, layout, jerarquía visual, estados vacíos/carga/error y módulos de “investigación guiada”.

**No implementar** comparador “antes/después” tipo slider (no viable). Mantener thumbnails como evidencia visual. Agregar gating de descarga de imágenes: requiere **registro/login** y plan/pago (si ya existe lógica; si no existe, mostrar UI y dejar todo como “disabled + tooltip” o “redirigir a login”).

---

## Cambios de UX/UI (requeridos)

### 1) Renombre y lenguaje
- En menú/topbar: cambiar “Auditoría” por **“Verificar terreno”**.
- Título principal (H1): **“Verificar terreno”**.
- Subtítulo:  
  “Investigá si una zona se incendió, cómo cambió la vegetación y qué señales quedan en el paisaje.”
- Reemplazar textos “auditoría” y “ejecutar auditoría” por “verificación” de forma consistente.

### 2) CTA principal
- Botón primario: texto exacto **“Verificá”**.
- Debe ser el CTA más visible del panel de control.

### 3) Reordenar el flujo: lugar → mapa → resultados
La UI debe reflejar el flujo natural:

**Paso 1: Buscar lugar**
- Agregar input principal “Buscar lugar” con placeholder:
  “Dirección, localidad, parque nacional o provincia”
- Debe aceptar texto libre. Si ya existe geocodificación/búsqueda, integrarla; si no existe aún, dejar input funcional como “controlador de estado” y mostrar helper “Buscá y seleccioná en el mapa”.

**Paso 2: Marcar punto en el mapa**
- Botón secundario: “Marcar punto en el mapa” (o “Seleccionar en el mapa” si ya existe, pero preferir “Marcar punto…”).
- El mapa debe tener prioridad visual (ver layout).

**Paso 3: Verificar**
- Click en **“Verificá”** ejecuta la verificación usando:
  - coordenadas del punto marcado (obligatorio)
  - área de análisis (obligatorio)

### 4) Cambiar “Radio (metros)” por “Área de análisis”
- Reemplazar campo “Radio (metros)” por selector más humano:
  - Chips/segment control:
    - **Alrededores (500 m)**
    - **Zona (1 km)**
    - **Amplio (3 km)**
  - Opción “Personalizar” abre input numérico en metros (esto puede quedar en “Avanzado” si querés simplificar).
- Guardar valor final como `radius_m`.

### 5) Coordenadas e ID catastral pasan a “Avanzado”
- La UI principal **no** debe empezar con lat/long.
- Crear un acordeón/sección colapsable: **“Opciones avanzadas”**
  - Dentro:
    - Latitud
    - Longitud
    - ID catastral
    - Input numérico de radio si se usa “Personalizar”
- El usuario no técnico debe poder completar todo sin tocar “Avanzado”.

---

## Layout (requerido)

### Estructura “2 columnas” (desktop)
- Columna izquierda (60–70%): **Mapa protagonista**
  - Mostrar mapa visible “above the fold”
  - Controles mínimos superpuestos o en barra superior del mapa: “Marcar punto”
- Columna derecha (30–40%): Panel de control + resultados
  - Bloque “Buscar lugar”
  - Bloque “Área de análisis”
  - Botón primario “Verificá”
  - Luego panel “Resultados” (con estado vacío/carga/error)

### Mobile
- Mapa primero.
- Panel de control y resultados como drawer o sección debajo del mapa (no es necesario animación compleja, pero mantener jerarquía).

---

## Experiencia de investigación (curiosidad guiada)

### 6) Leyendas estratégicas (microcopy)
Agregar textos cortos en lugares clave (sin saturar). Reglas:
- Tono: curioso, claro, no técnico.
- Evitar afirmar conspiraciones. Invitar a comparar evidencia.

**Ubicación sugerida A (debajo del subtítulo, texto pequeño):**
“Algunos incendios son accidentales; otros pueden tener intereses detrás. Acá podés mirar evidencia y sacar tus conclusiones.”

**Ubicación sugerida B (debajo del botón “Verificá” o en el panel de resultados):**
“Esto no demuestra intencionalidad por sí solo. Sirve para contrastar relatos con evidencia observable.”

### 7) Módulo “Checklist de verificación”
Agregar un componente tipo card en el panel de resultados (siempre visible, incluso sin resultados), con checklist:

**Título:** “Checklist de verificación”  
Items:
- “¿Hubo incendios en los últimos años en esta zona?”
- “¿La vegetación se recuperó o quedó degradada?”
- “¿Persisten señales del incendio en el área?”
- “¿Qué dicen fuentes públicas y registros locales?”

**Nota:** no incluir por ahora el campo opcional para pegar link del rumor.

---

## Resultados y estados (requeridos)

### 8) Estado vacío con ejemplo de valor
Antes de verificar, el panel “Resultados” no debe estar vacío. Debe mostrar:
- Un bloque “Lo que vas a ver” con bullets:
  - “Línea de tiempo de incendios detectados”
  - “Evolución de la vegetación (indicadores)”
  - “Galería de evidencia (thumbnails)”
  - “Señales a favor/en contra de recuperación”
- Un hint: “Marcá un punto en el mapa y presioná Verificá.”

### 9) Estado cargando (cuando corre la verificación)
Mostrar un estado de progreso con mensajes por etapa (aunque sea simulado si el backend responde de una sola vez):
- “Buscando incendios históricos…”
- “Calculando evolución de vegetación…”
- “Cargando evidencia visual…”

### 10) Estado error (sin punto / sin datos / falla backend)
- Sin punto seleccionado: “Primero marcá un punto en el mapa.”
- Sin datos: “No encontramos registros para esta zona. Probá ampliar el área de análisis.”
- Error técnico: mensaje breve + botón “Reintentar”.

---

## Evidencia visual y descarga (con gating)

### 11) Thumbnails: mantener, mejorar presentación
- Mostrar grilla de thumbnails con:
  - fecha
  - fuente (si existe)
  - nubosidad/quality (si existe)
- Añadir botón por imagen: **“Descargar”** (o “Ver en alta resolución”)
  - Si usuario no está logueado: al click redirigir a login o abrir modal “Iniciá sesión para descargar”.
  - Si logueado pero no tiene plan: modal “Disponible en plan Pro” + CTA “Ver planes”.
  - Si existe lógica real de permisos, conectarla; si no, implementar gating solo a nivel UI (disabled + tooltip + navegación).

**Importante:** no implementar comparador slider antes/después.

---

## Componentes a crear o modificar (sugerencia)
- `VerifyLandPage` (antes auditoría)
- `LocationSearchInput`
- `AnalysisAreaSelector` (chips 500/1000/3000 + “Personalizar” opcional)
- `AdvancedOptionsAccordion`
- `InvestigationHints` (microcopy)
- `VerificationChecklistCard`
- `ResultsPanel` con estados (empty/loading/success/error)
- `EvidenceThumbnailsGrid` + `DownloadGate`

---

## Criterios de aceptación
1) El usuario puede completar el flujo sin ver coordenadas.
2) El CTA principal dice exactamente “Verificá”.
3) El mapa se ve arriba y domina la pantalla en desktop.
4) El selector “Área de análisis” usa 500 m, 1 km, 3 km.
5) “Opciones avanzadas” contiene lat/long e ID catastral.
6) Existe estado vacío informativo, estado cargando con pasos, estado error accionable.
7) Existe checklist de verificación visible.
8) La galería de thumbnails tiene acción “Descargar” con gating por login/plan (aunque sea UI-only si falta backend).
9) No aparece la palabra “auditoría” en el contenido visible (idealmente también reemplazar en labels/rutas si aplica).

---

## Copy final (exacto)
- H1: “Verificar terreno”
- Subtítulo: “Investigá si una zona se incendió, cómo cambió la vegetación y qué señales quedan en el paisaje.”
- Placeholder buscador: “Dirección, localidad, parque nacional o provincia”
- Sección: “Área de análisis”
  - “Alrededores (500 m)”
  - “Zona (1 km)”
  - “Amplio (3 km)”
- Acordeón: “Opciones avanzadas”
- Botón principal: “Verificá”
- Card checklist: “Checklist de verificación”
- Microcopy A: “Algunos incendios son accidentales; otros pueden tener intereses detrás. Acá podés mirar evidencia y sacar tus conclusiones.”
- Microcopy B: “Esto no demuestra intencionalidad por sí solo. Sirve para contrastar relatos con evidencia observable.”

---

## Notas técnicas
- Mantener consistencia de estilos con el diseño actual (cards, espaciados, iconografía).
- Evitar introducir dependencias nuevas pesadas.
- Si ya existe una ruta pública/privada, asegurar que descargar requiera autenticación.
- Si hay i18n, agregar strings correspondientes.
