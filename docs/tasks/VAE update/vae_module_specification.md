# Especificación del módulo VAE: visualización, reglas y flujo de datos

Fecha: 2026-03-12
Versión: 1.0
Estado: borrador validado — todas las decisiones de negocio cerradas
Autor: Nicolás (lead técnico) + Claude (asesor arquitectónico)

---

## 1. Propósito de este documento

Definir con precisión qué información genera el módulo VAE, en qué páginas aparece, bajo qué condiciones se muestra, y cómo fluyen los datos desde el schema hasta la UI. Sirve como fuente de verdad para la implementación técnica y como referencia para auditoría legal.

---

## 2. Restricción legal transversal: ley 26.815 / 27.604

### 2.1 Contexto normativo

La ley 26.815 de manejo del fuego prohíbe la modificación del uso del suelo en áreas incendiadas por plazos de 30 a 60 años. La ley 27.604 endureció las restricciones, prohibiendo división, loteo o cualquier actividad agropecuaria distinta al uso previo al foco ígneo.

### 2.2 Riesgo técnico identificado

Las heurísticas de clasificación de cambio de uso del suelo en `vae_service.py` usan umbrales fijos sin dataset de verdad terrestre (ground truth). Esto genera riesgo de:

- **Falsos positivos:** clasificar una zona como "construcción" basándose solo en reflectancia, derivando en denuncias infundadas.
- **Falsos negativos:** omitir violaciones reales por limitaciones de los umbrales.
- **Impugnación judicial:** evidencia técnica vulnerable por falta de rigor científico demostrable.
- **Variabilidad fenológica:** suelo preparado para siembra puede confundirse con área desmontada para construcción.

### 2.3 Mitigaciones adoptadas

| Mitigación | Estado | Implementación |
|---|---|---|
| Todo resultado de cambio de uso es una "alerta de detección remota", no un hecho confirmado | **Decisión tomada** | Disclaimer legal en frontend (estático default + override dinámico desde API) |
| `is_potential_violation` genera flag visual mínimo + notificación interna, nunca acción automática hacia autoridades | **Decisión tomada** | Flag visual discreto + notificación interna al equipo |
| Agregar `confidence_score` numérico a `land_use_changes` para reemplazar clasificación binaria | **Decisión tomada** | Migración de schema pendiente |
| Validación cruzada con productos de referencia (IDERA, Copernicus) | **Pendiente** | Fase futura |
| Dataset de verdad terrestre con precision/recall por ecosistema | **Pendiente** | Fase futura |

### 2.4 Texto del disclaimer legal

> Los resultados presentados constituyen alertas generadas mediante detección remota satelital (Sentinel-2) y análisis automatizado de índices de vegetación. No reemplazan la verificación técnica y legal presencial. Su interpretación requiere validación por profesionales habilitados conforme a la ley 26.815 y su modificatoria 27.604.

Este texto se renderiza como default estático en el frontend. La API puede sobreescribirlo vía campo `legal_disclaimer` en la respuesta, permitiendo actualización sin deploy.

---

## 3. Decisiones de negocio cerradas

| # | Decisión | Resolución | Impacto |
|---|---|---|---|
| D-01 | Fórmula de recovery | Mantener `(current_ndvi / baseline_ndvi) * 100` (baseline ratio) | No se persiste nadir; labels deben decir "nivel de vegetación (% del baseline)" |
| D-02 | Umbrales unificados | 90 / 70 / 40 / 10 confirmados como definición de negocio | `recovery_thresholds.py` centralizado |
| D-03 | Exposición de violaciones | Mínima hasta tener dataset de validación | Solo texto discreto con disclaimer, sin badges rojos prominentes |
| D-04 | Acciones automáticas por violación | Flag visual + notificación interna | No se notifica a autoridades automáticamente |
| D-05 | Disclaimer legal | Default estático en frontend + override dinámico desde API | Campo `legal_disclaimer` en respuesta API |
| D-06 | Scheduling | Monthly + weekly-recent + episodios (escenario C) | 0.11% quota GEE diaria |
| D-07 | Backfill | Dos regímenes: semestral para históricos cerrados (pre dic 2025), mensual para recientes cerrados (dic 2025+). One-shot. Episodios activos cubiertos por scheduling regular. Fecha de corte: 2025-12-01. | ~3 040 req GEE totales |
| D-08 | Acceso anónimo a datos VAE | Badge de estado + gráfico NDVI básico públicos; violaciones solo con JWT | RLS diferenciada |
| D-09 | Summary público | Sí, para transparencia | `GET /monitoring/recovery/summary` sin JWT |
| D-10 | Trigger manual | Sí, solo admin con rate limit (5 req/6h) | `POST /monitoring/recovery/trigger` |

---

## 4. Schema (estructura fundamental de datos)

### 4.1 Tabla `vegetation_monitoring` — estado actual en producción

```
fire_event_id       uuid NOT NULL (FK → fire_events)
satellite_image_id  uuid (FK → satellite_images)
month_number        smallint
monitoring_date     date NOT NULL
months_after_fire   integer
ndvi_mean           real
ndvi_min            real
ndvi_max            real
ndvi_std_dev        real
baseline_ndvi       real
recovery_percentage real
land_use_classification  varchar
classification_confidence real
classification_method    varchar
human_activity_detected  boolean
activity_type       varchar
activity_confidence varchar
notes               text
analyst_name        varchar
id                  uuid PK (default gen_random_uuid())
created_at          timestamptz
updated_at          timestamptz
cloud_cover_pct     real
recovery_status     varchar
```

**Columnas que NO existen y se necesitan:**

| Columna | Tipo | Propósito | Prioridad |
|---|---|---|---|
| `pending_reason` | `varchar(50)` | Diferenciar "en cola" vs "sin imágenes disponibles" | P2 |

**Constraints que NO existen y se necesitan:**

| Constraint | SQL | Propósito |
|---|---|---|
| UNIQUE compuesto | `UNIQUE (fire_event_id, monitoring_date)` | Idempotencia de upsert |
| Índice compuesto | `INDEX (fire_event_id, monitoring_date)` | Performance de queries |

### 4.2 Tabla `land_use_changes` — estado actual en producción

```
id                      uuid PK
fire_event_id           uuid NOT NULL (FK → fire_events)
monitoring_record_id    uuid (sin FK constraint)
change_detected_at      date NOT NULL
months_after_fire       integer
change_type             varchar NOT NULL
change_severity         varchar
before_image_id         uuid
after_image_id          uuid
change_detection_image_url text
affected_area_hectares  double precision
is_potential_violation  boolean DEFAULT false
violation_confidence    varchar
status                  varchar DEFAULT 'pending_review'
reviewed_by             varchar
reviewed_at             timestamptz
notes                   text
created_at              timestamptz
updated_at              timestamptz
```

**Columnas que NO existen y se necesitan:**

| Columna | Tipo | Propósito | Prioridad |
|---|---|---|---|
| `confidence_score` | `real` | Probabilidad numérica (0.0-1.0) para reemplazar clasificación binaria. Mitigación legal. | P1 |

**Constraints que NO existen y se necesitan:**

| Constraint | SQL | Propósito |
|---|---|---|
| UNIQUE compuesto | `UNIQUE (fire_event_id, change_detected_at)` | Idempotencia |
| FK a monitoring | `FOREIGN KEY (monitoring_record_id) REFERENCES vegetation_monitoring(id)` | Integridad referencial |
| NOT NULL | `ALTER COLUMN is_potential_violation SET NOT NULL` | Evitar nulls ambiguos |

### 4.3 Tabla `fire_events` — campo cacheado para badge en listado

Para evitar N+1 queries desde el feed principal (`FireCard`), el estado de recuperación debe cachearse:

| Columna | Tipo | Propósito |
|---|---|---|
| `latest_recovery_status` | `varchar` | Último `recovery_status` de `vegetation_monitoring`, actualizado por el worker |
| `latest_recovery_pct` | `real` | Último `recovery_percentage`, actualizado por el worker |

Estos campos se actualizan atómicamente al final de cada ejecución de `analyze_recovery`.

### 4.4 Umbrales unificados de clasificación

```
full_recovery:      ≥ 90%
advanced_recovery:  70% - 89%
moderate_recovery:  40% - 69%
early_recovery:     10% - 39%
stalled:            0% - 9%
not_started:        sin datos / pending
anomaly_detected:   cualquier anomalía activa
```

Fuente única: `app/core/recovery_thresholds.py`. Consumido por VAEService, workers y API.

---

## 5. Flow logic (reglas de proceso y workflows)

### 5.1 Flujo de recuperación (UC-F12 / UC-06)

```
celery-beat (cron)
    │
    ├── recovery-monthly (1er día del mes, todos los eventos activos)
    ├── recovery-weekly-recent (lunes, eventos < 6 meses)
    └── vae-episodes-weekly (miércoles, agregación por episodio)
         │
         ▼
    worker-gee (cola: vae)
         │
         ├── 1. Lee fire_event (centroid, start_date, perimeter)
         ├── 2. Construye bbox desde perimeter (no centroid)
         ├── 3. Busca baseline_ndvi en BD (reutiliza si existe)
         │      └── Si no existe: GEE get_best_image pre-incendio → calculate_ndvi
         │         └── Si falla: retorna {status: "pending", reason: "no_baseline_image"}
         ├── 4. Calcula NDVI actual: GEE get_best_image mes actual → calculate_ndvi
         │      └── Si falla: retorna {status: "pending", reason: "no_current_image"}
         ├── 5. Calcula recovery_pct = (current / baseline) * 100
         ├── 6. Clasifica recovery_status vía recovery_thresholds.py
         ├── 7. UPSERT en vegetation_monitoring (ON CONFLICT fire_event_id, monitoring_date)
         └── 8. UPDATE fire_events SET latest_recovery_status, latest_recovery_pct
```

### 5.2 Flujo de detección de cambio de uso (UC-F12 / UC-08)

```
celery-beat (cron)
    │
    └── vae-destruction-monthly
         │
         ▼
    worker-gee (cola: vae)
         │
         ├── 1. Lee fire_event + vegetation_monitoring (último registro)
         ├── 2. Evalúa heurísticas de cambio de uso
         │      ├── NDVI < 0.1 persistente > 12 meses → posible construcción
         │      ├── NDVI > baseline temprano (< 6 meses) → posible agricultura
         │      └── Otros patrones → natural_recovery
         ├── 3. Calcula confidence_score (0.0 - 1.0)
         ├── 4. UPSERT en land_use_changes
         └── 5. Si is_potential_violation = true → notificación interna
                (NO notificación a autoridades)
```

### 5.3 Flujo de backfill histórico

Fecha de corte: **2025-12-01**. Solo episodios **cerrados** (`extinct`, `closed`). Episodios activos cubiertos por scheduling regular.

```
Régimen A — episodios cerrados con start_date < 2025-12-01 (semestral):
    │
    ├── 1. Query: episodios cerrados sin registros en vegetation_monitoring
    │      WHERE start_date < '2025-12-01'
    │      AND status IN ('extinct', 'closed')
    │      ORDER BY: áreas protegidas primero (relevancia legal)
    ├── 2. Para cada episodio:
    │      ├── Generar puntos de análisis cada 6 meses desde start_date
    │      │   Ejemplo: incendio 2023-01 → 2023-07, 2024-01, 2024-07, 2025-01, 2025-07
    │      └── Para cada punto: ejecutar analyze_recovery
    ├── 3. Cap diario: 5 000 req GEE (compartido entre ambos regímenes)
    └── 4. Horario: madrugada UTC-3

Régimen B — episodios cerrados con start_date >= 2025-12-01 (mensual):
    │
    ├── 1. Query: episodios cerrados sin registros en vegetation_monitoring
    │      WHERE start_date >= '2025-12-01'
    │      AND status IN ('extinct', 'closed')
    ├── 2. Para cada episodio:
    │      ├── Generar puntos de análisis mensuales desde start_date
    │      │   Ejemplo: incendio 2025-12 → 2026-01, 2026-02, 2026-03
    │      └── Para cada punto: ejecutar analyze_recovery
    ├── 3. Ejecutar después de régimen A (prioridad a históricos)
    └── 4. Mismo cap diario compartido

Notas:
- Episodios activos NO entran en backfill (cubiertos por beat schedule).
- Episodios nuevos (2026+) que pasen a cerrado ya tendrán datos del
  scheduling regular; si tienen gaps, el beat schedule mensual los cubre.
- El backfill es one-shot: una vez completado, no se re-ejecuta.
- Consumo estimado: ~2 400 req GEE (régimen A) + ~640 (régimen B) = ~3 040 total.
```

### 5.4 Reglas de clasificación de anomalías

| Anomalía | Condición | Acción |
|---|---|---|
| `no_recovery` | recovery_pct < 10% después de 12 meses | Flag anomaly_detected |
| `rapid_greening` | recovery_pct > 80% en < 6 meses | Flag anomaly_detected (posible agricultura) |
| `sudden_drop` | NDVI cae a < 30% del baseline tras recuperación previa | Flag anomaly_detected |

---

## 6. Workers (componentes de ejecución)

### 6.1 Routing de colas — estado objetivo

```
worker-gee consume: analysis, vae
    ├── workers.tasks.recovery.*      → cola: vae
    ├── workers.tasks.destruction.*   → cola: vae
    ├── workers.tasks.carousel_task.* → cola: analysis
    ├── workers.tasks.geo_enrichment.*→ cola: analysis
    └── workers.tasks.exploration_hd.*→ cola: analysis

worker-fast consume: ingestion, clustering, reports, notification, default
```

**Corrección requerida:** eliminar toda referencia a cola `gee` en task_routes, decoradores y .apply_async(). Unificar en `vae`.

### 6.2 Beat schedule — estado objetivo

| Tarea | Schedule | Cola | Eventos procesados |
|---|---|---|---|
| `recovery-monthly` | 1er día del mes, 03:00 UTC-3 | vae | Todos los eventos activos (< 36 meses) |
| `recovery-weekly-recent` | Lunes, 04:00 UTC-3 | vae | Eventos < 6 meses |
| `vae-episodes-weekly` | Miércoles, 04:00 UTC-3 | vae | Agregación por episodio |
| `vae-destruction-monthly` | 15 del mes, 03:00 UTC-3 | vae | Todos los eventos activos |

### 6.3 Consumo estimado de quota GEE

| Tarea | Frecuencia | Eventos/ciclo | Req GEE/ciclo | Req GEE/mes |
|---|---|---|---|---|
| recovery-monthly | 1×/mes | ~200 | ~400 | 400 |
| recovery-weekly-recent | 4×/mes | ~50 | ~100 | 400 |
| vae-episodes-weekly | 4×/mes | ~30 | ~60 | 240 |
| vae-destruction-monthly | 1×/mes | ~200 | ~600 | 600 |
| **Total scheduling** | | | | **~1 640/mes** |
| **Backfill one-shot (régimen A)** | **1 vez** | **~300 históricos** | **~2 400** | **n/a** |
| **Backfill one-shot (régimen B)** | **1 vez** | **~80 recientes** | **~640** | **n/a** |

Esto representa 0.11% de la quota diaria. Margen amplio.

---

## 7. API (capa de interfaz)

### 7.1 Endpoints — estado objetivo

| Endpoint | Método | Auth | Descripción |
|---|---|---|---|
| `/api/v1/monitoring/recovery/{fire_event_id}` | GET | JWT | Serie NDVI completa + estado de recuperación |
| `/api/v1/monitoring/land-use-changes/{fire_event_id}` | GET | JWT | Cambios de uso detectados (incluye violaciones) |
| `/api/v1/monitoring/recovery/summary` | GET | **Público** | Resumen agregado para dashboard de transparencia |
| `/api/v1/monitoring/recovery/trigger` | POST | JWT + admin + rate limit (5/6h) | Disparo manual de análisis |

### 7.2 Contratos de respuesta

**GET /monitoring/recovery/{fire_event_id}** (requiere JWT):

```json
{
  "fire_event_id": "uuid",
  "recovery_status": "moderate_recovery",
  "recovery_metric": "baseline_ratio",
  "recovery_metric_description": "Porcentaje del NDVI pre-incendio alcanzado",
  "baseline_ndvi": 0.6,
  "current_ndvi": 0.35,
  "recovery_percentage": 58.3,
  "months_monitored": 12,
  "legal_disclaimer": "Los resultados presentados constituyen alertas...",
  "monitoring_data": [
    {
      "monitoring_date": "2023-07-01",
      "months_after_fire": 6,
      "ndvi_mean": 0.25,
      "recovery_percentage": 41.7,
      "cloud_cover_pct": 15.0,
      "recovery_status": "moderate_recovery"
    }
  ]
}
```

**GET /monitoring/land-use-changes/{fire_event_id}** (requiere JWT):

```json
{
  "fire_event_id": "uuid",
  "total_changes": 2,
  "violation_count": 1,
  "legal_disclaimer": "Los resultados presentados constituyen alertas...",
  "changes": [
    {
      "change_detected_at": "2023-06-15",
      "months_after_fire": 5,
      "change_type": "construction_detected",
      "change_severity": "critical",
      "affected_area_hectares": 12.5,
      "is_potential_violation": true,
      "confidence_score": 0.7,
      "status": "pending_review",
      "notes": "Alerta de detección remota — requiere verificación presencial"
    }
  ]
}
```

**GET /monitoring/recovery/summary** (público, sin JWT):

```json
{
  "total_monitored_events": 200,
  "status_breakdown": {
    "full_recovery": 15,
    "advanced_recovery": 45,
    "moderate_recovery": 80,
    "early_recovery": 40,
    "stalled": 10,
    "pending": 10
  },
  "average_recovery_percentage": 52.3,
  "legal_disclaimer": "..."
}
```

Nota: el summary público **no incluye** datos de violaciones ni cambios de uso.

### 7.3 Taxonomía de estados — unificada

Backend, workers y frontend usan la misma taxonomía:

```
not_started → pending → early_recovery → moderate_recovery →
advanced_recovery → full_recovery
                                        ↘ stalled
                                        ↘ anomaly_detected
```

**Gap actual:** el backend emite `excellent/good/moderate/poor/critical/suspicious/unknown` y el frontend espera `early_recovery/moderate_recovery/...`. Esta discrepancia debe resolverse: el backend debe emitir la taxonomía unificada.

---

## 8. UI (capa de presentación)

### 8.1 Matriz de visibilidad por página y rol

| Página | Ruta | Anónimo | Autenticado | Admin |
|---|---|---|---|---|
| **Home / feed** | `/` | Badge de estado en FireCard (colores neutros) | Badge de estado en FireCard | Igual que autenticado |
| **Detalle de evento** | `/fires/:id` | Badge de estado + gráfico NDVI básico (sin datos de violación) | Todo: badge + gráfico NDVI + tarjetas de cambio de uso + disclaimer | Igual + botón trigger manual |
| **Mapa** | `/map` | Marcadores estándar | Marcadores diferenciados para eventos con alerta (icono discreto) | Igual que autenticado |
| **Dashboard de monitoreo** | `/monitoring` (nueva) | Summary público: totales y distribución por estado | Summary + detalle por evento + filtros | Igual + acciones admin |

### 8.2 Componentes y condiciones de renderizado

#### `RecoveryStatusBadge` (en FireCard y FireDetail)

**Fuente de datos para el feed:** campo `latest_recovery_status` cacheado en `fire_events` (evita N+1 queries). No se hace fetch individual a `/monitoring/recovery/{id}` desde el listado.

**Mapeo visual:**

| Estado | Color | Label | Visible para anónimo |
|---|---|---|---|
| `not_started` | gris | Sin monitoreo | Sí |
| `pending` | gris claro | En proceso | Sí |
| `early_recovery` | amarillo | Recuperación temprana | Sí |
| `moderate_recovery` | amarillo-verde | Recuperación moderada | Sí |
| `advanced_recovery` | verde | Recuperación avanzada | Sí |
| `full_recovery` | verde oscuro | Recuperada | Sí |
| `stalled` | naranja | Estancada | Sí |
| `anomaly_detected` | naranja discreto | Requiere atención | Sí (sin detalle de qué anomalía) |

#### `RecoveryPanel` (en FireDetail)

Renderiza cuando: usuario autenticado AND no es detalle de episodio (`!isEpisodeDetail`).

Contenido:

- Tarjetas métricas: baseline NDVI, NDVI actual, % de vegetación, meses monitoreados.
- Gráfico NDVI temporal (`NdviChart`) con línea de baseline.
- Label "nivel de vegetación (% del baseline)" — no "recuperación".

#### `LandUseChangeCard` (en FireDetail, dentro de RecoveryPanel)

Renderiza cuando: usuario autenticado AND existen registros en `land_use_changes`.

**Exposición visual mínima (decisión D-03):**

- Texto descriptivo: tipo de cambio + fecha + meses post-incendio.
- **Sin badge rojo prominente.** Solo icono informativo discreto.
- `confidence_score` mostrado como "confianza: X%" en texto secundario.
- Disclaimer legal visible debajo de cada tarjeta.
- Si `status = 'pending_review'`: texto "pendiente de verificación presencial".

#### Marcadores en mapa (`FireMarkers`)

**Capacidad existente:** `FireMarkers.tsx` ya soporta `is_potential_violation` para diferenciación visual.
**Gap actual:** `MapPage.tsx` no inyecta ese campo en los map items.
**Corrección:** alimentar `is_potential_violation` desde el endpoint de episodios/eventos al construir map items. Solo visible para usuarios autenticados.

#### Dashboard de monitoreo (nueva página `/monitoring`)

Contenido público (sin JWT):

- Totales: eventos monitoreados, distribución por estado.
- Gráfico de distribución de estados de recuperación (barras o dona).
- Disclaimer legal.

Contenido autenticado (con JWT):

- Lista de eventos con filtros (provincia, estado, fecha).
- Links al detalle de cada evento.

### 8.3 Gráfico NDVI — especificación visual

**Anónimo:** gráfico de línea simple mostrando NDVI en el tiempo, con línea horizontal de baseline. Sin anotaciones de anomalías ni cambios de uso.

**Autenticado:** igual + anotaciones de puntos donde se detectaron anomalías o cambios de uso (markers sobre la línea).

### 8.4 Datos para anónimo vs autenticado — resumen

| Dato | Anónimo | Autenticado |
|---|---|---|
| Badge de estado de recuperación | Sí | Sí |
| Gráfico NDVI básico (línea + baseline) | Sí | Sí |
| Tarjetas métricas (baseline, current, %) | Sí | Sí |
| Tarjetas de cambio de uso | **No** | Sí |
| Datos de violaciones | **No** | Sí |
| Anotaciones de anomalías en gráfico | **No** | Sí |
| Summary agregado en dashboard | Sí | Sí |
| Detalle por evento en dashboard | **No** | Sí |
| Botón trigger manual | **No** | **Solo admin** |

---

## 9. Migración SQL requerida

```sql
-- 1. Constraints de idempotencia
ALTER TABLE vegetation_monitoring
  ADD CONSTRAINT uq_vm_event_date UNIQUE (fire_event_id, monitoring_date);

ALTER TABLE land_use_changes
  ADD CONSTRAINT uq_luc_event_date UNIQUE (fire_event_id, change_detected_at);

-- 2. Índices de performance
CREATE INDEX idx_vm_event_date ON vegetation_monitoring(fire_event_id, monitoring_date);
CREATE INDEX idx_vm_event_months ON vegetation_monitoring(fire_event_id, months_after_fire);
CREATE INDEX idx_luc_event ON land_use_changes(fire_event_id, change_detected_at);

-- 3. FK faltante
ALTER TABLE land_use_changes
  ADD CONSTRAINT land_use_changes_monitoring_record_id_fkey
  FOREIGN KEY (monitoring_record_id) REFERENCES vegetation_monitoring(id);

-- 4. NOT NULL en violation flag
ALTER TABLE land_use_changes
  ALTER COLUMN is_potential_violation SET NOT NULL;

-- 5. Nueva columna: confidence_score numérico
ALTER TABLE land_use_changes
  ADD COLUMN confidence_score real;

-- 6. Nueva columna: pending_reason
ALTER TABLE vegetation_monitoring
  ADD COLUMN pending_reason varchar(50);

-- 7. Campos cacheados en fire_events para badge en listado
ALTER TABLE fire_events
  ADD COLUMN latest_recovery_status varchar,
  ADD COLUMN latest_recovery_pct real;

-- 8. RLS
ALTER TABLE vegetation_monitoring ENABLE ROW LEVEL SECURITY;
CREATE POLICY "anon_read_vegetation" ON vegetation_monitoring
  FOR SELECT TO anon USING (true);
CREATE POLICY "auth_read_vegetation" ON vegetation_monitoring
  FOR SELECT TO authenticated USING (true);
CREATE POLICY "system_write_vegetation" ON vegetation_monitoring
  FOR ALL TO service_role USING (true) WITH CHECK (true);

ALTER TABLE land_use_changes ENABLE ROW LEVEL SECURITY;
CREATE POLICY "auth_read_land_use" ON land_use_changes
  FOR SELECT TO authenticated USING (true);
CREATE POLICY "system_write_land_use" ON land_use_changes
  FOR ALL TO service_role USING (true) WITH CHECK (true);
-- NOTA: anon NO puede leer land_use_changes (contiene datos de violaciones)
```

---

## 10. Matriz de trazabilidad completa

### 10.1 Worker → tabla → endpoint → componente UI

| Worker task | Tabla destino | Endpoint lector | Componente UI | Auth requerida |
|---|---|---|---|---|
| `analyze_recovery` | `vegetation_monitoring` + `fire_events` (cache) | `GET /monitoring/recovery/{id}` | `RecoveryPanel`, `NdviChart`, `RecoveryStatusBadge` | Badge: no. Panel completo: sí |
| `detect_destruction` | `land_use_changes` | `GET /monitoring/land-use-changes/{id}` | `LandUseChangeCard` | Sí |
| `batch_episode_recovery` | `vegetation_monitoring` (agregado) | `GET /monitoring/recovery/summary` | Dashboard `/monitoring` | Summary: no. Detalle: sí |

### 10.2 Página → dato → endpoint → auth

| Página | Dato mostrado | Endpoint | Auth gate |
|---|---|---|---|
| Home `/` | Badge de estado en FireCard | `GET /api/v1/fires` (campo `latest_recovery_status` incluido) | No (campo público) |
| Detalle `/fires/:id` — anónimo | Badge + gráfico NDVI + métricas | `GET /monitoring/recovery/{id}` | No para datos básicos |
| Detalle `/fires/:id` — autenticado | Badge + gráfico NDVI + métricas + cambios de uso + anotaciones | `GET /monitoring/recovery/{id}` + `GET /monitoring/land-use-changes/{id}` | Sí para violaciones |
| Mapa `/map` | Marcadores con diferenciación visual | Datos de episodios (campo `is_potential_violation` inyectado) | Diferenciación visual solo autenticado |
| Dashboard `/monitoring` — anónimo | Totales y distribución por estado | `GET /monitoring/recovery/summary` | No |
| Dashboard `/monitoring` — autenticado | Totales + lista filtrable + links a detalle | `GET /monitoring/recovery/summary` + listado | Sí para detalle |

---

## 11. Escenarios de validación

| ID | Escenario | Resultado esperado backend | Resultado esperado UI |
|---|---|---|---|
| VAE-01 | Evento sin registros en `vegetation_monitoring` | `200` con `recovery_status: "pending"`, `monitoring_data: []` | Badge gris "En proceso" |
| VAE-02 | Evento con serie NDVI (3 registros) | `200` con array ordenado cronológicamente | Gráfico de línea con 3 puntos + línea baseline |
| VAE-03 | Evento con `land_use_changes` + violación | `200` con `violation_count: 1` y disclaimer | Tarjeta de cambio discreta + disclaimer (solo autenticado) |
| VAE-04 | Usuario anónimo en `/fires/:id` | `200` con datos de recovery (sin violaciones) | Badge + gráfico NDVI. Sin tarjetas de cambio de uso |
| VAE-05 | Usuario anónimo en endpoint de violaciones | `401` | No aplica (frontend no hace el fetch) |
| VAE-06 | Admin ejecuta trigger | `202` job encolado | Confirmación en UI |
| VAE-07 | Admin excede rate limit de trigger | `429` | Mensaje "límite excedido, intente en X minutos" |
| VAE-08 | Worker ejecutado 2 veces para mismo evento/mes | 1 solo registro (upsert) | Sin duplicados en gráfico |
| VAE-09 | Worker sin imagen baseline disponible en GEE | Registro con `pending_reason: "no_baseline_image"` | Badge "Sin datos satelitales disponibles" |
| VAE-10 | Summary público accedido sin JWT | `200` con totales agregados (sin violaciones) | Dashboard de transparencia renderiza correctamente |

---

## 12. Roadmap de implementación

| Fase | Contenido | Dependencias | Prioridad |
|---|---|---|---|
| **F1: schema** | Migración SQL completa (sección 9) | Ninguna | P0 |
| **F2: umbrales** | `recovery_thresholds.py` + actualizar VAE/workers/API | F1 | P0 |
| **F3: colas** | Eliminar cola `gee`, unificar en `vae` | Ninguna | P0 |
| **F4: taxonomía** | Unificar estados backend ↔ frontend | F2 | P0 |
| **F5: workers** | Reescribir stubs → workers reales con persistencia | F1, F2, F3 | P1 |
| **F6: API** | Auth diferenciada (summary público, detalle JWT), disclaimer, modelos Pydantic | F4 | P1 |
| **F7: frontend básico** | Badge en FireCard, RecoveryPanel adaptado, NdviChart con baseline | F6 | P1 |
| **F8: violaciones** | LandUseChangeCard con exposición mínima + disclaimer | F5, F6 | P2 |
| **F9: mapa** | Inyectar `is_potential_violation` en map items | F5 | P2 |
| **F10: dashboard** | Nueva página `/monitoring` con summary público | F6 | P2 |
| **F11: backfill** | Tarea de backfill semestral con priorización por áreas protegidas | F5 | P2 |
| **F12: trigger** | Endpoint POST con admin + rate limit | F5 | P3 |
| **F13: confidence** | confidence_score en land_use_changes + UI | F8 | P3 |
| **F14: tests** | Suite completa: unit + integration + API | F5, F6 | P1 (paralelo) |
