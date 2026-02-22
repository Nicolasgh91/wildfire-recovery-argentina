# ForestGuard — tareas técnicas por correcciones canónicas (v4)

**Fuentes canónicas vigentes**
- `schema_v.4.sql`
- `0_master_plan.md`
- `0_episode_generation_flow.md`
- `1_arquitectura_final.md`

Este documento define las tareas técnicas necesarias para alinear el esquema y la lógica con las correcciones canónicas relevadas.

---

## Resumen de cambios necesarios

| Prioridad | Cambio | Tipo |
|---|---|---|
| P0 | Agregar `fire_events.last_seen_at` y backfill | `ALTER TABLE` + backfill |
| P0 | Unificar estados de `fire_events.status`: `controlled` → `monitoring`, `extinguished` → `extinct` y eliminar valores no canónicos | Migración + `ALTER` constraint |
| P1 | Insertar parámetros canónicos en `system_parameters` | `INSERT` (idempotente) |
| P1 | Enforzar semántica de `fire_episodes.end_date`: solo setear cuando `status = 'closed'` | `CHECK` o trigger |
| P2 | Documentar regla 1:N en `fire_episode_events` | Documentación |

---

## Convenciones de implementación

- Todas las migraciones deben ser **idempotentes** cuando sea posible.
- Si se toca un `CHECK` constraint en Postgres, se debe contemplar que el nombre del constraint puede variar por entorno. En esos casos:
  - localizarlo vía `pg_constraint`, y
  - dropearlo por nombre resuelto, o
  - crear un constraint nuevo con un nombre canónico y eliminar el anterior.
- Toda migración debe dejar el sistema en un estado consistente (sin filas con valores fuera del set canónico).

---

## FG-EP-20
### Agregar `last_seen_at` en `fire_events`

**Prioridad:** P0

### Objetivo
Alinear con la definición canónica: `fire_events.last_seen_at = MAX(fire_detections.detected_at)`.

### Cambios de esquema
```sql
ALTER TABLE public.fire_events
  ADD COLUMN IF NOT EXISTS last_seen_at timestamptz;

CREATE INDEX IF NOT EXISTS idx_fire_events_last_seen_at
  ON public.fire_events (last_seen_at DESC);
```

### Backfill
```sql
UPDATE public.fire_events e
SET last_seen_at = q.max_detected_at
FROM (
  SELECT d.fire_event_id, MAX(d.detected_at) AS max_detected_at
  FROM public.fire_detections d
  WHERE d.fire_event_id IS NOT NULL
  GROUP BY d.fire_event_id
) q
WHERE e.id = q.fire_event_id
  AND (e.last_seen_at IS NULL OR e.last_seen_at <> q.max_detected_at);
```

### Ajustes de lógica (backend)
- En el pipeline de recomputación de eventos, recalcular y persistir `last_seen_at`.
- En cualquier endpoint que derive “recencia” o “actividad”, usar `last_seen_at` como base temporal (cuando aplique).

### Criterios de aceptación
- [ ] La columna existe en todos los entornos.
- [ ] El backfill no deja `last_seen_at` nulo para eventos con detecciones.
- [ ] Existe índice para ordenar por recencia.

---

## FG-EP-21
### Normalización de estados de `fire_events.status`

**Prioridad:** P0

### Decisión canónica
- `fire_detections`: sin columna status.
- `fire_events.status` (canónico): `active | monitoring | extinct`.
- `fire_episodes.status` (canónico): `active | monitoring | extinct | closed`.

### Migración de datos
Mapeo:
- `controlled` → `monitoring`
- `extinguished` → `extinct`

```sql
UPDATE public.fire_events
SET status = 'monitoring'
WHERE status = 'controlled';

UPDATE public.fire_events
SET status = 'extinct'
WHERE status = 'extinguished';
```

### Actualización de constraint
1) Identificar el constraint actual del `CHECK` sobre `fire_events.status`.

```sql
SELECT conname
FROM pg_constraint
WHERE conrelid = 'public.fire_events'::regclass
  AND contype = 'c'
  AND pg_get_constraintdef(oid) ILIKE '%status%';
```

2) Reemplazar el constraint por uno canónico.

> Nota: el `DROP CONSTRAINT` requiere el nombre encontrado en el paso anterior.

```sql
ALTER TABLE public.fire_events
  ADD CONSTRAINT fire_events_status_check
  CHECK (status IN ('active','monitoring','extinct'));
```

Si existía un constraint previo con otro nombre, dropearlo:
```sql
-- Reemplazar <old_constraint_name> por el valor retornado por el SELECT
ALTER TABLE public.fire_events
  DROP CONSTRAINT IF EXISTS <old_constraint_name>;

-- Asegurar el constraint canónico
ALTER TABLE public.fire_events
  DROP CONSTRAINT IF EXISTS fire_events_status_check;
ALTER TABLE public.fire_events
  ADD CONSTRAINT fire_events_status_check
  CHECK (status IN ('active','monitoring','extinct'));
```

### Limpieza de columnas semánticamente “huérfanas”
En el esquema actual puede existir `extinguished_at`. Con la decisión canónica (sin `extinguished`), hay dos opciones válidas:

- **Opción A (recomendada):** renombrar a `extinct_at`.
  ```sql
  DO $$
  BEGIN
    IF EXISTS (
      SELECT 1 FROM information_schema.columns
      WHERE table_schema='public' AND table_name='fire_events' AND column_name='extinguished_at'
    ) AND NOT EXISTS (
      SELECT 1 FROM information_schema.columns
      WHERE table_schema='public' AND table_name='fire_events' AND column_name='extinct_at'
    ) THEN
      ALTER TABLE public.fire_events RENAME COLUMN extinguished_at TO extinct_at;
    END IF;
  END $$;
  ```

- **Opción B:** mantener `extinguished_at` pero actualizar documentación y uso. No recomendado (deja terminología vieja).

### Ajustes de código
- Revisar workers y API para:
  - no emitir `controlled` ni `extinguished`.
  - mapear cualquier input legacy a `monitoring` o `extinct`.
- Actualizar tests que asuman el set previo.

### Criterios de aceptación
- [ ] No existen filas con status fuera de `active|monitoring|extinct`.
- [ ] El `CHECK` constraint impide inserciones con estados legacy.
- [ ] El backend no produce ni espera `controlled` / `extinguished`.

---

## FG-EP-22
### Insertar parámetros canónicos en `system_parameters`

**Prioridad:** P1

### Objetivo
Alinear el catálogo de parámetros del sistema con los valores canónicos propuestos (sin romper los existentes).

### Parámetros a crear
- `event_spatial_epsilon_meters` = `2000`
- `event_temporal_window_hours` = `48`
- `event_monitoring_window_hours` = `168`
- `episode_spatial_epsilon_meters` = `6000` #Distancia típica entre eventos que aún pertenecen al mismo frente. Espacial episodio = 2× a 4× el espacial de evento
- `episode_temporal_window_hours` = `96`    #Tiempo máximo razonable para considerar continuidad sin detecciones activas. Temporal episodio = 2× a 3× la temporal de evento

### SQL (idempotente)
> El esquema exacto de `system_parameters` puede variar (por ejemplo: `key`, `value`, `value_num`, `value_json`). Ajustar el `INSERT` al modelo real.

Ejemplo genérico (key/value como texto):
```sql
INSERT INTO public.system_parameters (key, value)
VALUES
  ('event_spatial_epsilon_meters', '2000'),
  ('event_temporal_window_hours', '48'),
  ('event_monitoring_window_hours', '168'),
  ('episode_spatial_epsilon_meters', '6000'),
  ('episode_temporal_window_hours', '96')
ON CONFLICT (key) DO NOTHING;
```

### Ajustes de código
- Reemplazar valores hardcodeados (si existen) por lectura desde `system_parameters`.
- Asegurar valores por defecto en caso de ausencia (para backwards compatibility).

### Criterios de aceptación
- [ ] Los parámetros existen en base y son consultables.
- [ ] Los workers usan estos parámetros (o fallback seguro).

---

## FG-EP-23
### Enforzar semántica de `end_date` en `fire_episodes`

**Prioridad:** P1

### Regla canónica
`end_date` se setea **solo** cuando `status = 'closed'` (merge o cierre manual).

### Alternativa 1: constraint `CHECK` (simple)
```sql
ALTER TABLE public.fire_episodes
  DROP CONSTRAINT IF EXISTS fire_episodes_end_date_closed_check;

ALTER TABLE public.fire_episodes
  ADD CONSTRAINT fire_episodes_end_date_closed_check
  CHECK (
    (status = 'closed' AND end_date IS NOT NULL)
    OR
    (status <> 'closed' AND end_date IS NULL)
  );
```

### Alternativa 2: trigger (más flexible)
Permite, por ejemplo, setear `end_date = now()` automáticamente al pasar a `closed`.

```sql
CREATE OR REPLACE FUNCTION public.enforce_episode_end_date()
RETURNS trigger AS $$
BEGIN
  IF NEW.status = 'closed' THEN
    IF NEW.end_date IS NULL THEN
      NEW.end_date := now();
    END IF;
  ELSE
    NEW.end_date := NULL;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_enforce_episode_end_date ON public.fire_episodes;
CREATE TRIGGER trg_enforce_episode_end_date
BEFORE INSERT OR UPDATE OF status, end_date ON public.fire_episodes
FOR EACH ROW EXECUTE FUNCTION public.enforce_episode_end_date();
```

### Criterios de aceptación
- [ ] No se pueden persistir episodios con `status != 'closed'` y `end_date` no nulo.
- [ ] En cierre manual o merge, `end_date` queda correctamente seteado.

---

## FG-EP-24
### Documentar regla 1:N de `fire_episode_events`

**Prioridad:** P2

### Contexto
La tabla `fire_episode_events` permite M:N por su estructura, pero la regla de negocio define 1:N: **un `fire_event` solo puede pertenecer a un `fire_episode` a la vez**.

### Acción
- Documentar la regla en:
  - `1_tech_tasks_final.md` (sección de relaciones), y
  - documentación de API si existe endpoint de asignación.
- Agregar un test de integración en backend que falle si un evento queda asignado a más de un episodio.

### (Opcional) Enforzar en base
Si se decide enforzar en base, agregar un unique index:
```sql
CREATE UNIQUE INDEX IF NOT EXISTS ux_fire_episode_events_event_id
  ON public.fire_episode_events (fire_event_id);
```

---

## Paquete de migración sugerido

Crear una carpeta:
`/migrations/episode_refactor_v4_corrections/`

Archivos recomendados:
1. `001_add_fire_events_last_seen_at.sql` (FG-EP-20)
2. `002_normalize_fire_events_status.sql` (FG-EP-21)
3. `003_system_parameters_canonical.sql` (FG-EP-22)
4. `004_enforce_episode_end_date.sql` (FG-EP-23)
5. `README.md` con:
   - orden de ejecución,
   - rollback strategy,
   - validaciones post-migración.

