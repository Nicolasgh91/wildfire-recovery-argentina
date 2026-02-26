# Carrusel: estado actual, causa raíz y plan de acción (URLs vacías + hardening)

**Proyecto:** ForestGuard — carrusel de thumbnails en home  
**Alcance:** Diagnóstico, reparación de datos y mejoras estructurales (resiliencia, calidad de dato, UX).  
**Documento único:** análisis original + evaluación y propuesta de solución integrada.

---

## 1. Estado actual documentado

### 1.1 Síntoma en producción

- En el home, cada tarjeta del carrusel muestra la leyenda **"Imagen en procesamiento..."** y **no se ven imágenes**.
- La base de datos tiene episodios con `slides_data` de **3 elementos** (rgb, swir, nbr) y `jsonb_array_length(slides_data) > 0`, por lo que la API los incluye en `GET /fire-episodes?mode=active`.
- Ejemplo real de `slides_data` por episodio: cada slide tiene `type`, `generated_at`, `satellite_image_id`, y **`thumbnail_url: ""`** (cadena vacía).

### 1.2 Flujo de datos de punta a punta

```
Celery Beat (cron 00:00 ART)
  → generate_carousel
    → ImageryService.run_carousel()
      → Por episodio: GEE download_thumbnail (x3: SWIR, RGB, NBR)
      → Storage.upload_bytes() → UploadResult(success=True/False, url="..." o "")
      → Persistencia: fire_episodes.slides_data, satellite_images
API GET /fire-episodes?mode=active
  → Filtra: slides_data IS NOT NULL AND jsonb_array_length(slides_data) > 0
  → Devuelve episodios (incluidos los con thumbnail_url vacío)
Frontend FireCard
  → slides = allSlides.filter(slide => slide.thumbnail_url || slide.url)
  → Si slides.length === 0 pero allSlides.length > 0 → "Imagen en procesamiento..."
```

### 1.3 Cadena de causa raíz

| Eslabón | Componente | Comportamiento |
|--------|------------|----------------|
| 1 | `app/services/storage_service.py` | En `upload_bytes`, si `put_object` lanza (OCI/credenciales, NoSuchBucket), retorna `UploadResult(success=False, url="")` en lugar de relanzar. |
| 2 | `app/services/imagery_service.py` (antes del fix) | No validaba `upload_result.success` ni `url`. Persistía `""` en `slides_data` y en `satellite_images`. |
| 3 | BD | `fire_episodes.slides_data` con 3 objetos `thumbnail_url: ""`; filas en `satellite_images` con URLs vacías. |
| 4 | `app/api/routes/episodes.py` | Filtra solo `slides_data IS NOT NULL` y `jsonb_array_length > 0`; no exige al menos una URL no vacía. |
| 5 | `frontend/src/components/fires/fire-card.tsx` | Filtra por `thumbnail_url || slide.url`; cadena vacía es falsy → `slides` vacío → "Imagen en procesamiento...". |

**Conclusión:** Origen = upload fallido en storage + falta de validación al persistir. No hay URL válida para parchear desde metadata en los episodios afectados.

### 1.4 Correcciones ya implementadas

- **ImageryService** (`imagery_service.py`): Tras `_upload_thumbnail` se comprueba `upload_result.success` y que `(upload_result.url or "").strip()` no esté vacío. Si falla: `break`, rollback y limpieza de objetos subidos. No se vuelve a persistir `thumbnail_url` vacío.
- **Script** `scripts/maintenance/fix_carousel_empty_urls.py`: Modos `patch` (rellenar desde `satellite_images`) y `clear` (vaciar slides y borrar filas carousel para regenerar).

---

## 2. Alternativas de recuperación

- **Patch:** Rellenar `slides_data` desde `satellite_images` cuando la URL sí está en la tabla. En el escenario actual (upload fallido) no aplica: las filas también tienen URL vacía.
- **Clear (recomendado):** Vaciar `slides_data` y borrar filas carousel en `satellite_images`; luego ejecutar `generate_carousel` para regenerar. Rama correcta en producción: **clear → generate_carousel**.

---

## 3. Solución recomendada: tres fases

### Mapa de estado

**HECHO**

- `imagery_service.py` — validación de `upload_result.success` + url.
- `scripts/maintenance/fix_carousel_empty_urls.py` — script de reparación (patch / clear).

**PENDIENTE**

| Prioridad | Ítem | Descripción |
|-----------|------|-------------|
| 1 | Fase 1 | Ejecutar en producción: clear + regenerar carousel. |
| 2 | Fase 2a | Filtro SQL en `episodes.py`: excluir episodios donde todos los slides tienen URL vacía. |
| 3 | Fase 2b | Campo `slides_status` en `fire_episodes` (pending / processing / ready / failed). |
| 4 | Fase 2c | Retry con backoff en imagery_service por slide (no por episodio completo). |
| 5 | Fase 2d | Helper `_is_valid_url(url)` y usarlo antes de persistir en worker y script. |
| 6 | Fase 3 | UX en `fire-card.tsx` según `slides_status`: mensajes diferenciados y spinner. |

**Principio:** No resolver calidad de dato solo en frontend; el fix va en API + worker.

---

## 4. Fase 1 — Reparar datos (una sola ejecución)

Comandos concretos:

```bash
# 1. Inventario
python scripts/maintenance/fix_carousel_empty_urls.py --dry-run

# 2. Aplicar clear
python scripts/maintenance/fix_carousel_empty_urls.py --mode clear --dry-run
python scripts/maintenance/fix_carousel_empty_urls.py --mode clear

# 3. Regenerar carousel
docker exec -it forestguard-worker-analysis \
  celery -A workers.celery_app call workers.tasks.carousel_task.generate_carousel \
  --kwargs='{"force_refresh": true}'
```

Verificación: tras el run, comprobar en BD que los episodios tengan `slides_data` con `thumbnail_url` no vacíos y en la UI que las tarjetas muestren imágenes.

---

## 5. Fase 2 — Hardening del pipeline

### 5.1 Filtro en la API (prioridad 1)

**Problema:** El listado verifica que `slides_data` tenga elementos, pero no que al menos uno tenga URL válida. Eso permite que datos corruptos lleguen al frontend.

**Cambio en** `app/api/routes/episodes.py` (filtro para `mode=active`): además de `slides_data IS NOT NULL` y `jsonb_array_length(slides_data) > 0`, exigir que exista al menos un slide con `thumbnail_url` no null y no vacío. Ejemplo:

```python
# Añadir al bloque if mode_value == "active":
text("""
    EXISTS (
        SELECT 1 FROM jsonb_array_elements(fire_episodes.slides_data) AS s
        WHERE (s->>'thumbnail_url') IS NOT NULL
          AND (s->>'thumbnail_url') != ''
    )
""")
```

Costo bajo, impacto alto: el frontend deja de recibir episodios "en procesamiento" que en realidad fallaron.

### 5.2 Estado explícito por episodio (prioridad 2)

**Campo** `slides_status` en `fire_episodes` con valores: `pending` | `processing` | `ready` | `failed`.

- Migración sugerida:

```sql
ALTER TABLE fire_episodes
ADD COLUMN slides_status TEXT DEFAULT 'pending'
CHECK (slides_status IN ('pending', 'processing', 'ready', 'failed'));
```

- En `imagery_service.py`: al iniciar procesamiento del episodio → `processing`; al commit exitoso de los 3 slides → `ready`; al fallo definitivo (tras reintentos) → `failed`. Backfill: episodios con al menos una URL válida en `slides_data` → `ready`; resto según criterio (p. ej. `pending` o `failed`).

Beneficios: frontend puede mostrar estados distintos; backend puede filtrar y monitorear con `SELECT count(*) ... GROUP BY slides_status`.

### 5.3 Retry con backoff por slide (prioridad 2)

En `imagery_service.py`, dentro del loop de `VISUALS`, reintentar solo el upload del slide fallido (no todo el episodio), con backoff exponencial (p. ej. 3 intentos, `time.sleep(2**attempt)`). Si tras los reintentos no hay `success` y URL válida, hacer `break` y tratar el episodio como generación parcial (rollback + limpieza de orphans).

### 5.4 Validación de URL válida (prioridad 2)

Definir un helper reutilizable (p. ej. en `imagery_service` o módulo compartido):

```python
def _is_valid_url(url: str | None) -> bool:
    return bool(url and url.strip() and url.startswith("http"))
```

Usar antes de escribir en `slides_data` y en `SatelliteImage`; en el script de mantenimiento, al decidir si un slide tiene URL recuperable.

---

## 6. Fase 3 — UX diferenciada (prioridad 3)

En `frontend/src/components/fires/fire-card.tsx`, cuando la API exponga `slides_status`:

| `slides_status` | Mensaje | Spinner |
|-----------------|---------|---------|
| `pending` | "Imagen en preparación" | No |
| `processing` | "Generando imágenes..." | Sí |
| `failed` | "Imagen no disponible" | No |
| `ready` | Mostrar carrusel | — |

Mientras no exista `slides_status`, mantener el comportamiento actual; con el filtro de la Fase 2a, los episodios con todos los slides vacíos dejarán de llegar al frontend.

---

## 7. Archivos clave

| Archivo | Rol |
|---------|-----|
| `app/services/storage_service.py` | Retorna `UploadResult(success=False, url="")` en fallo de upload. |
| `app/services/imagery_service.py` | Genera slides; ya valida success/url; pendiente retry y `_is_valid_url`. |
| `app/api/routes/episodes.py` | Listado activo; pendiente filtro EXISTS por URL válida. |
| `app/models/episode.py` | FireEpisode; pendiente columna `slides_status`. |
| `frontend/src/components/fires/fire-card.tsx` | Placeholder y mensajes; pendiente UX por `slides_status`. |
| `scripts/maintenance/fix_carousel_empty_urls.py` | Reparación patch/clear; puede usar `_is_valid_url`. |

---

## 8. Diagrama de decisión (reparación)

```
Episodios con thumbnail_url vacío
  → ¿URL válida en satellite_images?
      → Sí: --mode patch → UPDATE slides_data con URLs
      → No: --mode clear → slides_data = [], DELETE satellite_images carousel
            → Ejecutar generate_carousel
  → UI muestra imágenes (tras regenerar)
```

En producción actual (URLs vacías en ambos lados), la rama válida es **clear → generate_carousel**.
