## Core Preproceso de Imágenes — Manual para devs/ops

Este manual explica cómo operar y depurar el flujo de thumbnails, watermark y fixes de PNG corruptos.

### 1. Resumen del flujo

- **Objetivo**: generar y mantener actualizadas las imágenes que se usan en:
  - carrusel de la home (thumbnails RGB/SWIR/NBR),
  - vistas de detalle y exploración HD (assets derivados).
- **Pipeline lógico**:
  1. Selección de episodios candidatos (`gee_candidate = true`, prioridad por `gee_priority`).
  2. Selección de escena Sentinel‑2 por episodio vía `GEEService` (ventanas y thresholds de nubes).
  3. Render de thumbnails (RGB, SWIR, NBR) en 768×576.
  4. Aplicación opcional de watermark (texto de fecha + logo).
  5. Upload a storage (OCI / S3‑compatible) y actualización de `fire_episodes.slides_data`.

### 2. Arquitectura técnica

- **Servicios principales**:
  - `app/services/imagery_service.py`:
    - orquesta la selección de episodios y escenas,
    - genera thumbnails y los sube a storage,
    - actualiza `fire_episodes.slides_data`.
  - `app/services/gee_service.py`:
    - autenticación GEE,
    - búsqueda de escenas Sentinel‑2,
    - render de imágenes.
  - `app/services/storage_service.py`:
    - subida de bytes a OCI/S3 (`carousel/{episode_id}/...`).
  - `app/utils/watermark.py`:
    - `apply_watermark(...)` con soporte de feature flags:
      - `DISABLE_WATERMARK_ALL`,
      - `DISABLE_WATERMARK_LOGO`.
- **Documentos base**:
  - `PNG_CORRUPTION_FIX_SUMMARY.md` (root) y `docs/1_home/thumbnails/PNG_CORRUPTION_FIX_SUMMARY.md`.
  - `docs/1_home/thumbnails/WATERMARK_IMPLEMENTATION_SUMMARY.md`.
  - `docs/watermark_debugging_guide.md`.

### 3. Cómo correr el flujo en local (thumbnails)

Requisitos mínimos:

- Variables de entorno:
  - GEE (`GEE_SERVICE_ACCOUNT_EMAIL`, `GEE_PRIVATE_KEY_PATH`/`GEE_SERVICE_ACCOUNT_JSON`, `GEE_PROJECT_ID`).
  - Storage (`OCI_S3_ACCESS_KEY`, `OCI_S3_SECRET_KEY`, `OCI_S3_ENDPOINT_URL`, `STORAGE_BACKEND=oci`).
- Base de datos con episodios y eventos recientes.

Patrones habituales:

- **Regenerar episodios problemáticos desde scripts dedicados**  
  (según `PNG_CORRUPTION_FIX_SUMMARY.md` y `watermark_debugging_guide.md`):

```bash
# En el contenedor API (ejemplo tomado de la guía)
docker exec forestguard-api python scripts/regenerate_fixed_episode.py

# Regenerar un episodio con control fino del watermark
docker exec forestguard-api python scripts/regenerate_episode_no_watermark.py EPISODE_ID
docker exec forestguard-api python scripts/regenerate_episode_no_watermark.py EPISODE_ID --disable-logo
docker exec forestguard-api python scripts/regenerate_episode_no_watermark.py EPISODE_ID --disable-all
```

> Nota: algunos scripts se mencionan en la documentación (por ejemplo `deep_png_fix.py` o `diagnose_png_corruption.py`) pero pueden haberse movido o reemplazado en el repo. Ante dudas, priorizar siempre `app/utils/watermark.py` y el worker/pipeline real.

### 4. Feature flags de watermark

Las flags permiten aislar problemas sin detener el pipeline completo:

- En `.env` o `docker-compose.yml`:

```bash
# Desactivar solo el logo (mantiene texto de fecha)
DISABLE_WATERMARK_LOGO=true

# Desactivar todo el watermark (logo + texto)
DISABLE_WATERMARK_ALL=true
```

- Comportamiento:
  - Normal (sin flags): logo + texto.
  - `DISABLE_WATERMARK_LOGO=true`: solo texto.
  - `DISABLE_WATERMARK_ALL=true`: se devuelve la imagen original sin modificaciones.

### 5. Checks de salud y validaciones mínimas

- **BD**:

```sql
-- Episodios con slides generados
SELECT id, status, gee_candidate,
       jsonb_array_length(slides_data) AS slides
FROM fire_episodes
WHERE gee_candidate
  AND status IN ('active', 'monitoring')
ORDER BY gee_priority DESC NULLS LAST
LIMIT 20;
```

- **Storage**:
  - Verificar que las URLs en `slides_data` responden (HTTP 200).
  - Probar apertura con `PIL.Image.open(...)` como en `watermark_debugging_guide.md`.

### 6. Flujos habituales de trabajo

- **Caso “generar carrusel nuevo después de fixes”**:
  1. Aplicar cambios necesarios en `imagery_service`/`watermark`.
  2. (Opcional) Activar flags de watermark según necesidad.
  3. Regenerar episodios afectados (`regenerate_fixed_episode.py` / `regenerate_episode_no_watermark.py`).
  4. Verificar en BD + abrir URLs resultantes.
  5. Validar visualmente en la home.

Para diagnósticos más profundos, ver `core-preproceso-runbook.md`.

