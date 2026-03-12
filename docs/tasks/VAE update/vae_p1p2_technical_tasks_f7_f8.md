# Tareas técnicas: fases F7 y F8 (prioridad P1/P2)

Fecha: 2026-03-12
Prerrequisitos: F1-F6 completados (schema, umbrales, colas, taxonomía, workers, API)
Referencia: `vae_module_specification.md` sección 8

---

## Estado actual del frontend (AS-IS confirmado)

Componentes que **ya existen:**

| Componente | Archivo | Estado |
|---|---|---|
| `RecoveryStatusBadge` | `frontend/src/components/monitoring/RecoveryStatusBadge.tsx` | Existe con taxonomía correcta (`early_recovery`, etc.) + fallback a `not_started` |
| `RecoveryPanel` | `frontend/src/components/monitoring/RecoveryPanel.tsx` | Existe, llama `useRecovery` + `useLandUseChanges`, gate por auth + `!isEpisodeDetail` |
| `NdviChart` | `frontend/src/components/ndvi-chart.tsx` | Existe pero con interfaz incompatible (`month: string, value: number`) |
| `useRecovery` hook | `frontend/src/hooks/queries/useRecovery.ts` | Existe, consume `GET /monitoring/recovery/{id}` |
| `useLandUseChanges` hook | `frontend/src/hooks/queries/useLandUseChanges.ts` | Existe, consume `GET /monitoring/land-use-changes/{id}` |
| `monitoring.ts` endpoints | `frontend/src/services/endpoints/monitoring.ts` | Existe con ambos endpoints definidos |
| Integración en `FireDetail` | `frontend/src/pages/FireDetail.tsx:413-415` | Existe con gate `isAuthenticated && !isEpisodeDetail` |
| `FireMarkers` violation support | `frontend/src/components/map/layers/FireMarkers.tsx:27,93` | Existe el soporte visual, pero `MapPage` no inyecta el campo |

Componentes/integraciones que **NO existen:**

| Gap | Descripción |
|---|---|
| Badge en `FireCard` del feed | Home (`/`) usa `fire-card` que no tiene `RecoveryStatusBadge` |
| Datos en mapa | `MapPage.tsx:77` no inyecta `is_potential_violation` en map items |
| NdviChart compatible con API | Interfaz actual es `{month: string, value: number}`, API retorna `{monitoring_date, ndvi_mean, recovery_percentage}` |
| Línea de baseline en NdviChart | Solo tiene `ReferenceLine` fija en y=0.5, no el baseline real |
| Acceso anónimo a datos básicos | `RecoveryPanel` solo renderiza con auth; decisión D-08 requiere badge + gráfico NDVI para anónimos |
| Disclaimer legal en UI | No existe componente ni texto de disclaimer |

---

## F7: frontend básico (badge, panel, gráfico NDVI)

### F7-01: adaptar NdviChart para formato real del API

**Archivo:** `frontend/src/components/ndvi-chart.tsx`

**Estado actual (línea ~14-16):**
```tsx
interface NdviChartProps {
  data: { month: string; value: number }[]
}
```

**Cambio requerido:**

```tsx
interface MonitoringDataPoint {
  monitoring_date: string;
  months_after_fire: number;
  ndvi_mean: number;
  recovery_percentage: number | null;
  cloud_cover_pct: number | null;
  recovery_status: string;
}

interface NdviChartProps {
  data: MonitoringDataPoint[];
  baselineNdvi: number | null;
  /** Si true, muestra anotaciones de anomalías (solo autenticado) */
  showAnnotations?: boolean;
}
```

**Cambios en el componente:**

1. **Eje X:** usar `monitoring_date` formateado (ej: "Ene 24", "Jul 24") en vez de `month`.
2. **Eje Y:** usar `ndvi_mean` en vez de `value`.
3. **Línea de baseline:** `ReferenceLine` dinámica con `y={baselineNdvi}` y label "Baseline pre-incendio". Eliminar la fija en 0.5.
4. **Tooltip:** mostrar `ndvi_mean`, `recovery_percentage`, `cloud_cover_pct`, fecha formateada.
5. **Gradiente de color** en área bajo la curva: zonas por debajo de `baselineNdvi * 0.4` en rojo suave, entre 0.4 y 0.9 en amarillo, encima de 0.9 en verde.

```tsx
// Ejemplo de estructura (Recharts):
<ResponsiveContainer width="100%" height={250}>
  <AreaChart data={formattedData}>
    <defs>
      {/* Gradiente para el área */}
      <linearGradient id="ndviGradient" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stopColor="#22c55e" stopOpacity={0.3} />
        <stop offset="100%" stopColor="#22c55e" stopOpacity={0.05} />
      </linearGradient>
    </defs>
    <XAxis
      dataKey="label"
      tick={{ fontSize: 11 }}
      interval="preserveStartEnd"
    />
    <YAxis domain={[0, 'auto']} tick={{ fontSize: 11 }} />
    <Tooltip content={<NdviTooltip />} />
    <Area
      type="monotone"
      dataKey="ndvi_mean"
      stroke="#22c55e"
      fill="url(#ndviGradient)"
      strokeWidth={2}
    />
    {baselineNdvi && (
      <ReferenceLine
        y={baselineNdvi}
        stroke="#6b7280"
        strokeDasharray="6 3"
        label={{
          value: `Baseline: ${baselineNdvi.toFixed(2)}`,
          position: "right",
          fontSize: 11,
          fill: "#6b7280",
        }}
      />
    )}
  </AreaChart>
</ResponsiveContainer>
```

**Tooltip personalizado:**
```tsx
function NdviTooltip({ active, payload }: any) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="rounded-lg border bg-card p-2 text-xs shadow-sm">
      <p className="font-medium">{d.dateFormatted}</p>
      <p>NDVI: {d.ndvi_mean?.toFixed(3)}</p>
      {d.recovery_percentage != null && (
        <p>Nivel de vegetación: {d.recovery_percentage.toFixed(1)}%</p>
      )}
      {d.cloud_cover_pct != null && (
        <p className="text-muted-foreground">Nubes: {d.cloud_cover_pct.toFixed(0)}%</p>
      )}
    </div>
  );
}
```

**Label del eje Y:** "NDVI" (no "recuperación").

**Verificación:**
```bash
grep -n "month: string.*value: number" frontend/src/components/ndvi-chart.tsx
# Esperado: 0 resultados (interfaz vieja eliminada)

grep -n "baselineNdvi\|monitoring_date\|ndvi_mean" frontend/src/components/ndvi-chart.tsx
# Esperado: múltiples resultados
```

---

### F7-02: adaptar RecoveryPanel para acceso anónimo parcial

**Archivo:** `frontend/src/components/monitoring/RecoveryPanel.tsx`

**Estado actual:** solo renderiza cuando `isAuthenticated && !isEpisodeDetail`.

**Cambio requerido según decisión D-08:** anónimos ven badge + gráfico NDVI + métricas. Autenticados ven todo eso + cambios de uso + anotaciones.

**Archivo:** `frontend/src/pages/FireDetail.tsx` (~línea 413-415)

Cambiar la condición de rendering:

```tsx
// ANTES:
{isAuthenticated && !isEpisodeDetail && (
  <RecoveryPanel fireEventId={fireEventId} />
)}

// DESPUÉS:
{!isEpisodeDetail && (
  <RecoveryPanel
    fireEventId={fireEventId}
    isAuthenticated={isAuthenticated}
  />
)}
```

**Archivo:** `frontend/src/components/monitoring/RecoveryPanel.tsx`

Agregar prop `isAuthenticated` y condicionar contenido:

```tsx
interface RecoveryPanelProps {
  fireEventId: string;
  isAuthenticated?: boolean;
}

export function RecoveryPanel({ fireEventId, isAuthenticated = false }: RecoveryPanelProps) {
  const { data: recovery, isLoading: recoveryLoading } = useRecovery(fireEventId);
  
  // Solo fetch de land-use changes si está autenticado
  const { data: changes } = useLandUseChanges(
    isAuthenticated ? fireEventId : null  // null desactiva el fetch
  );

  if (recoveryLoading) return <RecoveryPanelSkeleton />;
  if (!recovery) return null;

  return (
    <div className="space-y-4">
      {/* Sección pública: badge + métricas + gráfico */}
      <div className="flex items-center gap-2">
        <h3 className="text-lg font-medium">Nivel de vegetación</h3>
        <RecoveryStatusBadge status={recovery.recovery_status} />
      </div>

      {/* Métricas básicas — públicas */}
      <RecoveryMetricCards
        baselineNdvi={recovery.baseline_ndvi}
        currentNdvi={recovery.current_ndvi}
        recoveryPercentage={recovery.recovery_percentage}
        monthsMonitored={recovery.months_monitored}
      />

      {/* Gráfico NDVI — público */}
      {recovery.monitoring_data?.length > 0 && (
        <NdviChart
          data={recovery.monitoring_data}
          baselineNdvi={recovery.baseline_ndvi}
          showAnnotations={isAuthenticated}
        />
      )}

      {/* Sección privada: cambios de uso — solo autenticados */}
      {isAuthenticated && changes?.changes?.length > 0 && (
        <LandUseChangesSection changes={changes} />
      )}

      {/* Disclaimer legal — siempre visible */}
      <LegalDisclaimer text={recovery.legal_disclaimer} />
    </div>
  );
}
```

**Verificación:**
```bash
grep -n "isAuthenticated" frontend/src/components/monitoring/RecoveryPanel.tsx
# Esperado: al menos 3 (prop, destructuring, conditional)

grep -n "useLandUseChanges" frontend/src/components/monitoring/RecoveryPanel.tsx
# Esperado: condicional con isAuthenticated
```

---

### F7-03: crear componente RecoveryMetricCards

**Archivo nuevo:** `frontend/src/components/monitoring/RecoveryMetricCards.tsx`

```tsx
interface RecoveryMetricCardsProps {
  baselineNdvi: number | null;
  currentNdvi: number | null;
  recoveryPercentage: number | null;
  monthsMonitored: number;
}

export function RecoveryMetricCards({
  baselineNdvi,
  currentNdvi,
  recoveryPercentage,
  monthsMonitored,
}: RecoveryMetricCardsProps) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      <MetricCard
        label="NDVI baseline"
        value={baselineNdvi?.toFixed(3) ?? "—"}
        sublabel="Pre-incendio"
      />
      <MetricCard
        label="NDVI actual"
        value={currentNdvi?.toFixed(3) ?? "—"}
        sublabel="Último análisis"
      />
      <MetricCard
        label="Nivel de vegetación"
        value={
          recoveryPercentage != null
            ? `${recoveryPercentage.toFixed(1)}%`
            : "—"
        }
        sublabel="% del baseline"
      />
      <MetricCard
        label="Meses monitoreados"
        value={monthsMonitored.toString()}
        sublabel="Desde el incendio"
      />
    </div>
  );
}

function MetricCard({
  label,
  value,
  sublabel,
}: {
  label: string;
  value: string;
  sublabel: string;
}) {
  return (
    <div className="rounded-lg border bg-card p-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-xl font-semibold">{value}</p>
      <p className="text-xs text-muted-foreground">{sublabel}</p>
    </div>
  );
}
```

---

### F7-04: crear componente LegalDisclaimer

**Archivo nuevo:** `frontend/src/components/monitoring/LegalDisclaimer.tsx`

```tsx
const DEFAULT_DISCLAIMER =
  "Los resultados presentados constituyen alertas generadas mediante " +
  "detección remota satelital (Sentinel-2) y análisis automatizado de " +
  "índices de vegetación. No reemplazan la verificación técnica y legal " +
  "presencial. Su interpretación requiere validación por profesionales " +
  "habilitados conforme a la ley 26.815 y su modificatoria 27.604.";

interface LegalDisclaimerProps {
  text?: string | null;
}

export function LegalDisclaimer({ text }: LegalDisclaimerProps) {
  return (
    <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 dark:border-amber-900 dark:bg-amber-950">
      <p className="text-xs text-amber-800 dark:text-amber-200">
        {text || DEFAULT_DISCLAIMER}
      </p>
    </div>
  );
}
```

---

### F7-05: agregar badge de recovery en FireCard del feed

**Archivo:** el componente de card usado en `Home.tsx`

**Según AS-IS:** `Home.tsx:13` importa desde `components/fires/fire-card`. Este componente no tiene badge de recovery.

**Fuente de datos:** campo `latest_recovery_status` que ahora viene incluido en la respuesta de listado de eventos/episodios (F1-04c + F5-03 step 6). No se hace fetch individual.

**Cambio en el componente de card:**

```tsx
// Dentro del card, después de los badges existentes de severity/status:
import { RecoveryStatusBadge } from "@/components/monitoring/RecoveryStatusBadge";

// En el JSX del card:
{item.latest_recovery_status && (
  <RecoveryStatusBadge
    status={item.latest_recovery_status}
    size="sm"
  />
)}
```

**Cambio en `RecoveryStatusBadge`:** agregar prop `size` si no existe:

```tsx
interface RecoveryStatusBadgeProps {
  status: string;
  size?: "sm" | "md";
}

// En el render, ajustar clases según size:
const sizeClasses = size === "sm" ? "text-[10px] px-1.5 py-0.5" : "text-xs px-2 py-1";
```

**Verificación:**
```bash
grep -n "RecoveryStatusBadge\|latest_recovery_status" frontend/src/components/fires/fire-card.tsx
# Esperado: al menos 1 de cada uno
```

---

### F7-06: actualizar tipo del endpoint de listado de eventos

**Archivo:** `frontend/src/services/endpoints/` (el archivo que define el tipo de respuesta del listado de eventos)

Agregar campos al tipo de respuesta:

```tsx
interface FireEvent {
  // ... campos existentes ...
  latest_recovery_status?: string | null;
  latest_recovery_pct?: number | null;
}
```

Si el tipo se define inline o con una interfaz diferente, localizar y agregar los campos.

---

### F7-07: actualizar hook useRecovery para manejar acceso anónimo

**Archivo:** `frontend/src/hooks/queries/useRecovery.ts`

El endpoint `GET /monitoring/recovery/{id}` ahora funciona sin JWT (retorna datos básicos). El hook debe funcionar tanto con auth como sin auth. Dado que el interceptor de API ya agrega JWT solo si existe, no debería requerir cambios.

**Verificación:** confirmar que el interceptor en `api.ts:84-86` agrega header condicionalmente:
```bash
grep -A5 "Authorization\|token\|Bearer" frontend/src/services/api.ts
# Esperado: lógica condicional que solo agrega header si hay token
```

---

## F8: violaciones con exposición mínima

### F8-01: crear componente LandUseChangesSection

**Archivo nuevo:** `frontend/src/components/monitoring/LandUseChangesSection.tsx`

**Decisión D-03:** exposición visual mínima hasta tener dataset de validación. Sin badges rojos prominentes. Texto discreto + disclaimer.

```tsx
import { LegalDisclaimer } from "./LegalDisclaimer";

interface LandUseChange {
  change_detected_at: string;
  months_after_fire: number;
  change_type: string;
  change_severity: string;
  affected_area_hectares: number | null;
  is_potential_violation: boolean;
  confidence_score: number | null;
  status: string;
  notes: string | null;
}

interface LandUseChangesSectionProps {
  changes: {
    total_changes: number;
    violation_count: number;
    changes: LandUseChange[];
    legal_disclaimer?: string;
  };
}

// Mapeo de change_type a labels legibles
const CHANGE_TYPE_LABELS: Record<string, string> = {
  construction_detected: "Posible construcción detectada",
  agriculture: "Posible actividad agrícola",
  bare_soil: "Suelo descubierto persistente",
  natural_recovery: "Recuperación natural",
  uncertain: "Cambio no clasificado",
};

const SEVERITY_LABELS: Record<string, string> = {
  critical: "Severidad alta",
  high: "Severidad media-alta",
  medium: "Severidad media",
  low: "Severidad baja",
};

export function LandUseChangesSection({ changes }: LandUseChangesSectionProps) {
  if (!changes.changes.length) return null;

  return (
    <div className="space-y-3">
      <h4 className="text-sm font-medium text-muted-foreground">
        Cambios de uso de suelo detectados ({changes.total_changes})
      </h4>

      {changes.changes.map((change, i) => (
        <LandUseChangeCard key={i} change={change} />
      ))}

      <LegalDisclaimer text={changes.legal_disclaimer} />
    </div>
  );
}

function LandUseChangeCard({ change }: { change: LandUseChange }) {
  const dateFormatted = new Date(change.change_detected_at).toLocaleDateString(
    "es-AR",
    { year: "numeric", month: "short" }
  );

  return (
    <div className="rounded-lg border bg-card p-3 text-sm">
      <div className="flex items-start justify-between">
        <div>
          <p className="font-medium">
            {CHANGE_TYPE_LABELS[change.change_type] || change.change_type}
          </p>
          <p className="text-xs text-muted-foreground">
            {dateFormatted} — {change.months_after_fire} meses post-incendio
          </p>
        </div>

        {/* Indicador discreto — NO badge rojo prominente (decisión D-03) */}
        {change.is_potential_violation && (
          <span className="inline-flex items-center gap-1 text-xs text-amber-600 dark:text-amber-400">
            <InfoIcon className="h-3.5 w-3.5" />
            Requiere verificación
          </span>
        )}
      </div>

      {/* Detalles secundarios */}
      <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
        {change.change_severity && (
          <span>{SEVERITY_LABELS[change.change_severity] || change.change_severity}</span>
        )}
        {change.affected_area_hectares != null && (
          <span>{change.affected_area_hectares.toFixed(1)} ha</span>
        )}
        {change.confidence_score != null && (
          <span>Confianza: {(change.confidence_score * 100).toFixed(0)}%</span>
        )}
        <span className="capitalize">
          {change.status === "pending_review"
            ? "Pendiente de verificación presencial"
            : change.status}
        </span>
      </div>

      {change.notes && (
        <p className="mt-1.5 text-xs italic text-muted-foreground">
          {change.notes}
        </p>
      )}
    </div>
  );
}

// Icono info simple (o importar de lucide-react)
function InfoIcon({ className }: { className?: string }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 20 20"
      fill="currentColor"
      className={className}
    >
      <path
        fillRule="evenodd"
        d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a.75.75 0 000 1.5h.253a.25.25 0 01.244.304l-.459 2.066A1.75 1.75 0 0010.747 15H11a.75.75 0 000-1.5h-.253a.25.25 0 01-.244-.304l.459-2.066A1.75 1.75 0 009.253 9H9z"
        clipRule="evenodd"
      />
    </svg>
  );
}
```

**Puntos de diseño (decisión D-03):**

- Sin badge rojo prominente. Solo texto amber discreto "Requiere verificación" con icono info.
- `confidence_score` mostrado como porcentaje en texto secundario, no como indicador visual.
- Cada tarjeta tiene `notes` que dice "Alerta de detección remota — requiere verificación presencial".
- `pending_review` se traduce a "Pendiente de verificación presencial".
- El `LegalDisclaimer` aparece al final de la sección, reforzando que son alertas remotas.

**Verificación:**
```bash
# No debe haber badges rojos (bg-red, text-red con más de 1 uso)
grep -c "bg-red\|text-red-500\|text-red-600" frontend/src/components/monitoring/LandUseChangesSection.tsx
# Esperado: 0 (se usa amber, no red)

# Debe tener disclaimer
grep -n "LegalDisclaimer" frontend/src/components/monitoring/LandUseChangesSection.tsx
# Esperado: al menos 1
```

---

### F8-02: condicionar fetch de land-use changes al auth

**Archivo:** `frontend/src/hooks/queries/useLandUseChanges.ts`

Verificar que el hook acepta `null` para desactivar el fetch:

```tsx
export function useLandUseChanges(fireEventId: string | null) {
  return useQuery({
    queryKey: ["land-use-changes", fireEventId],
    queryFn: () => monitoringEndpoints.getLandUseChanges(fireEventId!),
    enabled: !!fireEventId,  // no fetch si null
  });
}
```

Si el hook actual no acepta `null`, agregar esa posibilidad. Esto se conecta con F7-02 donde `RecoveryPanel` pasa `null` cuando `!isAuthenticated`.

**Verificación:**
```bash
grep -n "enabled" frontend/src/hooks/queries/useLandUseChanges.ts
# Esperado: al menos 1 resultado con lógica condicional
```

---

### F8-03: inyectar is_potential_violation en marcadores del mapa

**Archivo:** `frontend/src/pages/MapPage.tsx` (~línea 77)

**Estado actual:** `MapPage` construye map items sin el campo `is_potential_violation`.

**Cambio:** agregar el campo desde los datos del episodio/evento. Dado que `land_use_changes` requiere JWT, esta información solo está disponible para autenticados.

**Estrategia:** en vez de hacer un fetch adicional de `land_use_changes` por cada marker (N+1), usar un enfoque batch. Dos opciones:

**Opción A (recomendada — campo cacheado):** si el backend incluye un flag `has_violation` en la respuesta de listado de episodios, usarlo directamente. Esto requiere un campo adicional en la API de episodios (similar a `latest_recovery_status` en `fire_events`).

**Opción B (pragmática — sin cambio backend):** hacer un solo fetch a un endpoint batch cuando el usuario está autenticado.

Para esta fase, recomendar **opción A** con un campo `has_active_violation` en el endpoint de episodios. Esto implica un cambio menor en el backend (agregar al query de episodios un LEFT JOIN a `land_use_changes`).

**Cambio en MapPage (independiente de la opción):**

```tsx
// En la función que construye map items (~línea 77):
const mapItem = {
  // ... campos existentes ...
  is_potential_violation: isAuthenticated
    ? (episode.has_active_violation ?? false)
    : false,  // anónimos no ven diferenciación
};
```

**Verificación:**
```bash
grep -n "is_potential_violation" frontend/src/pages/MapPage.tsx
# Esperado: al menos 1 resultado

grep -n "is_potential_violation" frontend/src/types/map.ts
# Verificar que el tipo incluye el campo (puede necesitar agregarse)
```

---

### F8-04: agregar campo al tipo MapItem

**Archivo:** `frontend/src/types/map.ts` (~línea 18)

Verificar si `is_potential_violation` ya existe en el tipo. Si no:

```tsx
interface MapItem {
  // ... campos existentes ...
  is_potential_violation?: boolean;
}
```

---

## Verificación integral F7 + F8

### Checklist visual (manual)

| Escenario | Página | Qué verificar |
|---|---|---|
| Anónimo en Home `/` | Feed | Badge de recovery visible en FireCard (colores neutros) |
| Anónimo en `/fires/:id` | Detalle | Badge + métricas + gráfico NDVI visible. Sin tarjetas de cambio de uso |
| Anónimo en `/fires/:id` | Detalle | Disclaimer legal visible debajo del gráfico |
| Autenticado en `/fires/:id` | Detalle | Todo lo anterior + tarjetas de cambio de uso (si existen) |
| Autenticado en `/fires/:id` con violación | Detalle | Tarjeta de cambio con texto amber "Requiere verificación" (NO badge rojo) |
| Autenticado en `/map` | Mapa | Marcadores diferenciados para eventos con alerta (si hay datos) |
| Anónimo en `/map` | Mapa | Marcadores estándar sin diferenciación |
| Evento sin datos VAE | Detalle | Badge gris "En proceso" + métricas con "—" + sin gráfico |
| Evento con 3 registros NDVI | Detalle | Gráfico con 3 puntos, línea de baseline, tooltip funcional |

### Checklist de código

```bash
# 1. NdviChart usa nueva interfaz
grep -n "monitoring_date\|ndvi_mean\|baselineNdvi" frontend/src/components/ndvi-chart.tsx
# Esperado: múltiples resultados

# 2. RecoveryPanel acepta anónimos
grep -n "isAuthenticated" frontend/src/components/monitoring/RecoveryPanel.tsx
# Esperado: al menos 2

# 3. FireCard tiene badge
grep -n "RecoveryStatusBadge\|latest_recovery_status" frontend/src/components/fires/fire-card.tsx
# Esperado: al menos 1

# 4. No hay badges rojos en LandUseChangesSection
grep -c "bg-red\|text-red" frontend/src/components/monitoring/LandUseChangesSection.tsx
# Esperado: 0

# 5. LegalDisclaimer existe y se usa
find frontend/src -name "LegalDisclaimer*" -type f
# Esperado: al menos 1

grep -rn "LegalDisclaimer" frontend/src/components/monitoring/
# Esperado: al menos 2 (definición + uso)

# 6. Labels correctos (no "recuperación")
grep -rn '"Recuperación"' frontend/src/components/monitoring/
# Esperado: 0 (debe decir "Nivel de vegetación" o equivalente)
```

---

## Orden de ejecución F7 + F8

```
F7-01 (NdviChart) ──────────────┐
F7-03 (RecoveryMetricCards) ────┤
F7-04 (LegalDisclaimer) ────────┤── Componentes nuevos/adaptados (paralelo)
F8-01 (LandUseChangesSection) ──┘
                                 │
F7-02 (RecoveryPanel anónimo) ──┤── Integración (después de componentes)
F7-06 (tipo FireEvent) ─────────┤
F7-07 (hook useRecovery) ───────┘
                                 │
F7-05 (badge en FireCard) ──────┤── Integraciones en páginas
F8-02 (hook useLandUseChanges) ─┤
F8-03 (MapPage violation) ──────┤
F8-04 (tipo MapItem) ───────────┘

Deploy: un solo build de frontend + push a GHCR.
No requiere cambios en backend (asume F1-F6 ya desplegados).
```

---

## Resumen de archivos afectados

| Archivo | Tipo de cambio | Fase |
|---|---|---|
| `frontend/src/components/ndvi-chart.tsx` | Modificación mayor (interfaz + render) | F7-01 |
| `frontend/src/components/monitoring/RecoveryPanel.tsx` | Modificación (prop + condicionales) | F7-02 |
| `frontend/src/components/monitoring/RecoveryMetricCards.tsx` | **Nuevo** | F7-03 |
| `frontend/src/components/monitoring/LegalDisclaimer.tsx` | **Nuevo** | F7-04 |
| `frontend/src/components/fires/fire-card.tsx` | Modificación menor (agregar badge) | F7-05 |
| `frontend/src/services/endpoints/` (tipos) | Modificación menor (agregar campos) | F7-06 |
| `frontend/src/pages/FireDetail.tsx` | Modificación menor (quitar gate auth del panel) | F7-02 |
| `frontend/src/components/monitoring/LandUseChangesSection.tsx` | **Nuevo** | F8-01 |
| `frontend/src/hooks/queries/useLandUseChanges.ts` | Modificación menor (null support) | F8-02 |
| `frontend/src/pages/MapPage.tsx` | Modificación menor (inyectar campo) | F8-03 |
| `frontend/src/types/map.ts` | Modificación menor (agregar campo) | F8-04 |
