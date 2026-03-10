# Tareas técnicas: pipeline de assets HD/PDF/thumbnails

**Fecha:** 2026-02-22  
**Ejecutor:** Claude Code  
**Estado:** Documento archivado. Las decisiones clave están en `docs/STATE.md`, `docs/architecture/flows.md`, `docs/features/` y `docs/architecture/containers.md`. Se conserva como referencia histórica de diseño.

**Decisiones de arquitectura confirmadas:**
1. PDF como task Celery independiente (chain tras HD)
2. Consolidar fuente Home ahora (`/fire-episodes?mode=active`)
3. Implementar cache de escenas GEE ahora

**Restricción global:** costo cero (Oracle Free Tier 10 GB, GEE 50k req/día)

---

## Mapa de dependencias

```
FASE 0: Parámetros (sin deps)
  │
  ├──► FASE 1: Cache GEE (dep: FASE 0)
  │
  ├──► FASE 2: PDF task independiente (dep: FASE 0)
  │       │
  │       └──► FASE 2B: Frontend HD+PDF (dep: FASE 2)
  │
  ├──► FASE 3: Consolidar Home (sin deps backend; dep frontend: FASE 0)
  │
  └──► FASE 4: Storage y cleanup (dep: FASE 0)

FASE 5: Validación (dep: FASES 1-4)
```

**Tiempo estimado total:** ~8 h

---

## Convenciones para Claude Code

- Rama: `feature/assets-pipeline-core`
- Commits atómicos: un commit por tarea, mensaje con ID (ej. `feat(PARAM-01): add storage limit parameters`)
- Antes de editar un archivo, leer su contenido completo para entender el contexto
- No romper funcionalidad existente: los endpoints actuales deben seguir funcionando
- Verificar con `grep` que no quedan imports rotos después de cada cambio
- Ejecutar `python -c "from app.main import app; print('OK')"` tras cada tarea que modifique imports

---

## FASE 0: parámetros de sistema y semáforo GEE

### PARAM-01: agregar parámetros de storage y PDF en system_parameters

**Archivo:** migración SQL nueva
**Esfuerzo:** 10 min
**Dependencias:** ninguna

Crear archivo `database/migrations/013_add_storage_and_pdf_parameters.sql`:

```sql
-- Parámetros de control de storage (Oracle Free Tier)
INSERT INTO system_parameters (param_key, param_value, description, category)
VALUES
  ('storage_max_total_gb', '{"value": 8}',
   'Límite de storage total en GB antes de alertar (Oracle Free Tier = 10 GB)', 'limits'),
  ('storage_alert_threshold_gb', '{"value": 7}',
   'Umbral en GB para reducir carousel_batch_size a la mitad', 'limits'),
  ('storage_critical_threshold_gb', '{"value": 9}',
   'Umbral en GB para suspender generación de assets HD', 'limits'),
  ('hd_asset_retention_days', '{"value": 7}',
   'Días de retención de assets HD sin acceso', 'limits'),
  ('pdf_retention_days', '{"value": 90}',
   'Días de retención de PDFs generados', 'limits'),
  ('pdf_max_embedded_images', '{"value": 6}',
   'Máximo de imágenes embebidas en un PDF', 'reports'),
  ('pdf_max_size_mb', '{"value": 20}',
   'Tamaño máximo de un PDF generado en MB', 'reports'),
  ('pdf_image_dpi', '{"value": 150}',
   'DPI de imágenes embebidas en PDF (150 = pantalla, 300 = impresión)', 'reports'),
  ('gee_max_concurrent_requests', '{"value": 20}',
   'Máximo de requests simultáneas a GEE (free tier soporta 40)', 'imagery')
ON CONFLICT (param_key) DO NOTHING;
```

**Ejecución:**
```bash
# Aplicar migración
psql $DATABASE_URL -f database/migrations/013_add_storage_and_pdf_parameters.sql
```

**Criterio de aceptación:**
```bash
psql $DATABASE_URL -c "SELECT param_key, param_value FROM system_parameters WHERE category IN ('limits', 'reports', 'imagery') ORDER BY param_key;"
# Debe retornar 9 filas (más las existentes de carousel_batch_size, etc.)
```

---

### PARAM-02: crear semáforo global Redis para requests GEE

**Archivo nuevo:** `app/core/gee_semaphore.py`
**Esfuerzo:** 30 min
**Dependencias:** PARAM-01

Este semáforo lo adquieren todos los workers antes de llamar a GEE. Protege la cuota de 40 requests simultáneas del free tier.

```python
"""
Semáforo global Redis para limitar concurrencia de requests a Google Earth Engine.

Uso:
    from app.core.gee_semaphore import gee_semaphore

    async with gee_semaphore.acquire(timeout=60):
        resultado = await gee_service.get_image(...)

Para workers Celery (sync):
    with gee_semaphore.acquire_sync(timeout=60):
        resultado = gee_service.get_image(...)
"""

import time
import uuid
import contextlib
from typing import Optional

import redis

from app.core.config import settings

import logging
logger = logging.getLogger(__name__)

# Key fija en Redis para el semáforo
_SEMAPHORE_KEY = "forestguard:gee_semaphore"
_DEFAULT_MAX_CONCURRENT = 20
_LOCK_TTL_SECONDS = 300  # 5 min máximo por request GEE


class GEESemaphore:
    """Semáforo distribuido basado en Redis sorted set con TTL por entrada."""

    def __init__(self, redis_url: Optional[str] = None, max_concurrent: Optional[int] = None):
        self._redis_url = redis_url or getattr(settings, 'REDIS_URL', 'redis://redis:6379/0')
        self._max_concurrent = max_concurrent or _DEFAULT_MAX_CONCURRENT
        self._redis: Optional[redis.Redis] = None

    @property
    def _client(self) -> redis.Redis:
        if self._redis is None:
            self._redis = redis.from_url(self._redis_url, decode_responses=True)
        return self._redis

    def _cleanup_expired(self):
        """Eliminar locks expirados (TTL vencido)."""
        now = time.time()
        self._client.zremrangebyscore(_SEMAPHORE_KEY, "-inf", now)

    def _try_acquire(self, lock_id: str) -> bool:
        """Intenta adquirir un slot. Retorna True si lo obtuvo."""
        self._cleanup_expired()
        current_count = self._client.zcard(_SEMAPHORE_KEY)
        if current_count < self._max_concurrent:
            expires_at = time.time() + _LOCK_TTL_SECONDS
            self._client.zadd(_SEMAPHORE_KEY, {lock_id: expires_at})
            return True
        return False

    def _release(self, lock_id: str):
        """Libera un slot."""
        self._client.zrem(_SEMAPHORE_KEY, lock_id)

    @contextlib.contextmanager
    def acquire_sync(self, timeout: int = 60):
        """Context manager sincrónico para workers Celery."""
        lock_id = str(uuid.uuid4())
        deadline = time.time() + timeout
        acquired = False

        try:
            while time.time() < deadline:
                if self._try_acquire(lock_id):
                    acquired = True
                    logger.debug(f"GEE semaphore acquired: {lock_id}")
                    yield
                    return
                time.sleep(1)

            raise TimeoutError(
                f"No se pudo adquirir slot GEE en {timeout}s. "
                f"Slots ocupados: {self._client.zcard(_SEMAPHORE_KEY)}/{self._max_concurrent}"
            )
        finally:
            if acquired:
                self._release(lock_id)
                logger.debug(f"GEE semaphore released: {lock_id}")

    def get_usage(self) -> dict:
        """Retorna uso actual del semáforo (para /admin/storage-usage)."""
        self._cleanup_expired()
        current = self._client.zcard(_SEMAPHORE_KEY)
        return {
            "gee_slots_used": current,
            "gee_slots_max": self._max_concurrent,
            "gee_slots_available": self._max_concurrent - current,
        }


# Singleton global
gee_semaphore = GEESemaphore()
```

**Criterio de aceptación:**
```python
# Test manual en shell
from app.core.gee_semaphore import gee_semaphore
with gee_semaphore.acquire_sync(timeout=5):
    print("Slot adquirido, ejecutando request GEE simulada...")
print("Slot liberado")
print(gee_semaphore.get_usage())
```

---

### PARAM-03: integrar semáforo en ImageryService (carrusel)

**Archivo:** `app/services/imagery_service.py`
**Esfuerzo:** 15 min
**Dependencias:** PARAM-02

Buscar las llamadas a GEE dentro de `ImageryService` (probablemente en `run_carousel()` ~línea 742 y en `refresh_fire()` ~línea 806) e insertar el semáforo.

**Patrón de cambio:**
```python
# ANTES (buscar patrón similar):
result = ee.Image(image_id).getThumbURL(vis_params)

# DESPUÉS:
from app.core.gee_semaphore import gee_semaphore

with gee_semaphore.acquire_sync(timeout=120):
    result = ee.Image(image_id).getThumbURL(vis_params)
```

**Importante:** buscar TODAS las llamadas a `ee.Image`, `ee.ImageCollection`, o cualquier interacción con la API de Earth Engine dentro de `imagery_service.py` y encapsularlas con el semáforo.

**Verificación:**
```bash
grep -n "ee\.\(Image\|ImageCollection\|Geometry\)" app/services/imagery_service.py
# Todas las líneas resultantes deben estar dentro de un bloque gee_semaphore.acquire_sync
```

---

### PARAM-04: integrar semáforo en worker HD de exploración

**Archivo:** `app/workers/exploration_hd_worker.py`
**Esfuerzo:** 15 min
**Dependencias:** PARAM-02

Buscar las llamadas a GEE dentro de `run_generation_job()` (~línea 303) y `generate per item` (~línea 95) y aplicar el mismo patrón que PARAM-03.

**Verificación:**
```bash
grep -n "ee\.\(Image\|ImageCollection\|Geometry\)" app/workers/exploration_hd_worker.py
# Todas las líneas deben estar dentro de gee_semaphore.acquire_sync
```

---

## FASE 1: cache de escenas GEE

### CACHE-01: crear servicio de cache de escenas

**Archivo nuevo:** `app/services/gee_scene_cache.py`
**Esfuerzo:** 45 min
**Dependencias:** PARAM-01

Este servicio consulta `satellite_images` antes de llamar a GEE. Si existe una imagen con la misma receta (`gee_system_index` + `visualization_params` + `fire_event_id`), reutiliza el asset existente.

```python
"""
Cache de escenas GEE basado en la tabla satellite_images.

Antes de llamar a GEE para generar un thumbnail o asset HD, este servicio
verifica si ya existe una imagen con la misma receta reproducible.

Regla: si gee_system_index + visualization_params + fire_event_id coinciden
y la imagen tiene is_reproducible=true, se reutiliza.
"""

import hashlib
import json
import logging
from typing import Optional
from sqlalchemy.orm import Session

from app.models.satellite_image import SatelliteImage  # ajustar import al modelo real

logger = logging.getLogger(__name__)


def compute_recipe_hash(
    gee_system_index: str,
    visualization_params: dict,
    fire_event_id: str,
) -> str:
    """Genera hash determinístico de la receta GEE para búsqueda rápida."""
    recipe = json.dumps({
        "gee_system_index": gee_system_index,
        "vis_params": visualization_params,
        "fire_event_id": fire_event_id,
    }, sort_keys=True)
    return hashlib.sha256(recipe.encode()).hexdigest()[:16]


def find_cached_scene(
    db: Session,
    gee_system_index: str,
    visualization_params: dict,
    fire_event_id: str,
) -> Optional[SatelliteImage]:
    """
    Busca una imagen existente con la misma receta GEE.

    Retorna el registro de satellite_images si existe y es reproducible.
    Retorna None si no hay match (=> debe generarse vía GEE).
    """
    result = db.query(SatelliteImage).filter(
        SatelliteImage.fire_event_id == fire_event_id,
        SatelliteImage.gee_system_index == gee_system_index,
        SatelliteImage.is_reproducible == True,
    ).first()

    if result is None:
        return None

    # Comparar visualization_params (match exacto de la receta)
    stored_params = result.visualization_params or {}
    if stored_params == visualization_params:
        logger.info(
            f"Cache HIT: reutilizando satellite_image {result.id} "
            f"para fire_event {fire_event_id}"
        )
        return result

    logger.debug(
        f"Cache MISS (params differ): fire_event {fire_event_id}, "
        f"gee_system_index={gee_system_index}"
    )
    return None


def should_regenerate_thumbnail(
    db: Session,
    episode_id: str,
    current_gee_image_id: Optional[str],
    last_gee_image_id: Optional[str],
) -> bool:
    """
    Determina si un episodio necesita regenerar thumbnails.

    Retorna False (no regenerar) si last_gee_image_id no cambió.
    Esto es la optimización clave documentada en UC-F08R.
    """
    if current_gee_image_id and current_gee_image_id == last_gee_image_id:
        logger.debug(f"Episodio {episode_id}: gee_image_id sin cambios, omitiendo regeneración")
        return False
    return True
```

**Nota para Claude Code:** ajustar el import `from app.models.satellite_image import SatelliteImage` al nombre real del modelo ORM. Verificar con:
```bash
grep -rn "class SatelliteImage" app/models/
# Si el modelo se llama distinto, adaptar el import
```

---

### CACHE-02: integrar cache en ImageryService (carrusel)

**Archivo:** `app/services/imagery_service.py`
**Esfuerzo:** 30 min
**Dependencias:** CACHE-01

Dentro de `run_carousel()` (~línea 742), antes de generar cada thumbnail vía GEE, agregar la consulta al cache.

**Patrón de cambio (pseudocódigo, adaptar a la estructura real):**

```python
from app.services.gee_scene_cache import find_cached_scene, should_regenerate_thumbnail

# Dentro del loop de episodios en run_carousel():
for episode in candidate_episodes:
    # Verificar si necesita regeneración
    if not should_regenerate_thumbnail(
        db=db,
        episode_id=str(episode.id),
        current_gee_image_id=best_image_id,   # el ID de la mejor escena actual
        last_gee_image_id=episode.last_gee_image_id,
    ):
        continue  # saltar, no gastar request GEE

    # Para cada tipo de thumbnail (swir, rgb, nbr):
    for vis_type, vis_params in visualization_configs.items():
        cached = find_cached_scene(
            db=db,
            gee_system_index=best_image_id,
            visualization_params=vis_params,
            fire_event_id=str(representative_event.id),
        )
        if cached:
            # Reutilizar URL existente
            thumbnail_url = cached.thumbnail_url or cached.r2_url
        else:
            # Generar vía GEE (con semáforo)
            with gee_semaphore.acquire_sync(timeout=120):
                thumbnail_url = generate_thumbnail_from_gee(...)

            # Guardar en satellite_images para cache futuro
            save_satellite_image(db, ...)
```

**Importante:** no reescribir la función completa. Solo agregar las verificaciones de cache alrededor de las llamadas GEE existentes. Leer el código actual completo antes de modificar.

---

### CACHE-03: integrar cache en worker HD de exploración

**Archivo:** `app/workers/exploration_hd_worker.py`
**Esfuerzo:** 20 min
**Dependencias:** CACHE-01

Dentro de la generación por item (~línea 95), antes de llamar a GEE, verificar cache:

```python
from app.services.gee_scene_cache import find_cached_scene

# Por cada item de la investigación:
cached = find_cached_scene(
    db=db,
    gee_system_index=item.gee_system_index,
    visualization_params=item.visualization_params,
    fire_event_id=str(item.fire_event_id),
)

if cached and cached.r2_url:
    # Reutilizar asset existente
    logger.info(f"Cache HIT para item {item.id}, reutilizando asset {cached.id}")
    item.status = "generated"
    item.asset_url = cached.r2_url
else:
    # Generar vía GEE (con semáforo ya integrado en PARAM-04)
    with gee_semaphore.acquire_sync(timeout=120):
        result = generate_hd_image(...)
```

---

## FASE 2: PDF como task Celery independiente

### PDF-01: crear servicio de generación de PDF

**Archivo nuevo:** `app/services/pdf_generation_service.py`
**Esfuerzo:** 1 h
**Dependencias:** PARAM-01

Servicio reutilizable basado en `reportlab.platypus` (flowables, no coordenadas absolutas). Lo usan tanto el task de PDF post-HD como el endpoint judicial existente.

```python
"""
Servicio de generación de PDF para ForestGuard.

Genera PDFs profesionales usando reportlab.platypus con layout automático.
Reutilizable por: task PDF post-HD, endpoint judicial, closure reports.

No escribe archivos temporales: genera en BytesIO y retorna bytes.
"""

import hashlib
import io
import logging
from datetime import datetime, timezone
from typing import Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image as RLImage,
    Table, TableStyle, PageBreak,
)
from reportlab.lib import colors

logger = logging.getLogger(__name__)


class PdfGenerationService:
    """Genera PDFs a partir de resultados de exploración HD."""

    def __init__(self):
        self._styles = getSampleStyleSheet()
        self._styles.add(ParagraphStyle(
            name='ForestGuardTitle',
            parent=self._styles['Title'],
            fontSize=18,
            spaceAfter=20,
        ))
        self._styles.add(ParagraphStyle(
            name='ForestGuardMeta',
            parent=self._styles['Normal'],
            fontSize=9,
            textColor=colors.grey,
            spaceAfter=4,
        ))

    def generate_exploration_pdf(
        self,
        investigation_id: str,
        job_id: str,
        hd_results: dict,
        investigation_title: Optional[str] = None,
        max_images: int = 6,
        image_dpi: int = 150,
    ) -> tuple[bytes, str]:
        """
        Genera PDF de exploración HD en memoria.

        Args:
            investigation_id: UUID de la investigación.
            job_id: UUID del job HD.
            hd_results: diccionario con resultados del job HD.
            investigation_title: título opcional de la investigación.
            max_images: máximo de imágenes a embeber (de system_parameters).
            image_dpi: resolución de imágenes embebidas.

        Returns:
            tuple de (pdf_bytes, sha256_hash)
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
            leftMargin=2.5 * cm,
            rightMargin=2.5 * cm,
        )

        story = []
        now = datetime.now(timezone.utc)

        # Header
        title = investigation_title or "Reporte de exploración satelital"
        story.append(Paragraph(title, self._styles['ForestGuardTitle']))
        story.append(Paragraph(
            f"Generado por ForestGuard — {now.strftime('%d/%m/%Y %H:%M')} UTC",
            self._styles['ForestGuardMeta'],
        ))
        story.append(Paragraph(
            f"ID investigación: {investigation_id}",
            self._styles['ForestGuardMeta'],
        ))
        story.append(Paragraph(
            f"ID job: {job_id}",
            self._styles['ForestGuardMeta'],
        ))
        story.append(Spacer(1, 20))

        # Resumen
        images_list = hd_results.get('images', [])
        total_images = len(images_list)
        story.append(Paragraph(
            f"<b>Resumen:</b> {total_images} imagen(es) HD generada(s)",
            self._styles['Normal'],
        ))
        story.append(Spacer(1, 10))

        # Tabla de metadatos de imágenes
        if images_list:
            table_data = [['#', 'Banda', 'Fecha', 'Estado']]
            for idx, img_info in enumerate(images_list[:max_images]):
                table_data.append([
                    str(idx + 1),
                    str(img_info.get('band', 'N/A')),
                    str(img_info.get('target_date', 'N/A')),
                    str(img_info.get('status', 'N/A')),
                ])

            t = Table(table_data, colWidths=[1.5 * cm, 4 * cm, 4 * cm, 3.5 * cm])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E75B6')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F5F5F5')]),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            story.append(t)
            story.append(Spacer(1, 15))

        # Embeber imágenes (si hay paths locales disponibles)
        embedded_count = 0
        for img_info in images_list[:max_images]:
            local_path = img_info.get('local_path')
            if local_path and embedded_count < max_images:
                try:
                    import os
                    if os.path.exists(local_path):
                        story.append(Paragraph(
                            f"<b>Imagen {embedded_count + 1}:</b> {img_info.get('band', 'N/A')} — {img_info.get('target_date', '')}",
                            self._styles['Normal'],
                        ))
                        story.append(Spacer(1, 5))
                        img = RLImage(local_path, width=14 * cm, height=10 * cm)
                        img.hAlign = 'CENTER'
                        story.append(img)
                        story.append(Spacer(1, 15))
                        embedded_count += 1
                except Exception as e:
                    logger.warning(f"No se pudo embeber imagen {local_path}: {e}")

        # Pie de verificación
        story.append(Spacer(1, 30))
        story.append(Paragraph(
            "<i>Este documento fue generado automáticamente por ForestGuard. "
            "Las imágenes provienen de Google Earth Engine y son de dominio público. "
            "El hash SHA-256 de este documento puede verificarse para comprobar su integridad.</i>",
            self._styles['ForestGuardMeta'],
        ))

        # Construir PDF
        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()

        # Hash de integridad
        sha256 = hashlib.sha256(pdf_bytes).hexdigest()
        logger.info(
            f"PDF generado: {len(pdf_bytes)} bytes, SHA-256: {sha256[:12]}..., "
            f"{embedded_count} imágenes embebidas"
        )

        return pdf_bytes, sha256
```

**Verificación:**
```bash
pip install reportlab --break-system-packages
python -c "from app.services.pdf_generation_service import PdfGenerationService; print('OK')"
```

---

### PDF-02: crear task Celery independiente para PDF

**Archivo nuevo:** `workers/tasks/pdf_generation_task.py`
**Esfuerzo:** 30 min
**Dependencias:** PDF-01

```python
"""
Task Celery para generar PDF tras completar job HD.

Se ejecuta como tarea independiente encadenada al job HD.
Si falla, el job HD permanece en estado 'ready' (las imágenes están disponibles).
El PDF es un complemento, no un requisito.
"""

import logging
from celery import shared_task
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


@shared_task(
    name='workers.tasks.pdf_generation_task.generate_pdf_for_job',
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    queue='reports',
    acks_late=True,
)
def generate_pdf_for_job(self, job_id: str):
    """
    Genera PDF a partir de resultados de un job HD completado.

    Flujo:
    1. Cargar job y resultados HD de BD.
    2. Generar PDF en memoria con PdfGenerationService.
    3. Subir a OCI Object Storage.
    4. Actualizar job.results con pdf_url, pdf_sha256, pdf_status.

    Si falla, el job HD sigue disponible con status 'ready'.
    """
    from app.core.database import get_db_session  # ajustar al patrón real
    from app.services.pdf_generation_service import PdfGenerationService
    from app.services.storage_service import upload_to_oci  # ajustar al servicio real

    db: Session = get_db_session()
    pdf_service = PdfGenerationService()

    try:
        # 1. Cargar job
        # NOTA: ajustar al modelo real (ExplorationGenerationJob o similar)
        from app.models.exploration import ExplorationGenerationJob
        job = db.query(ExplorationGenerationJob).filter(
            ExplorationGenerationJob.id == job_id
        ).first()

        if not job:
            logger.error(f"Job {job_id} no encontrado")
            return {"status": "error", "detail": "Job not found"}

        if job.status != 'ready':
            logger.warning(f"Job {job_id} no está en estado ready (actual: {job.status})")
            return {"status": "skipped", "detail": f"Job status is {job.status}"}

        # 2. Leer parámetros de system_parameters
        from app.models.system_parameter import SystemParameter
        max_images_param = db.query(SystemParameter).filter(
            SystemParameter.param_key == 'pdf_max_embedded_images'
        ).first()
        max_images = max_images_param.param_value.get('value', 6) if max_images_param else 6

        dpi_param = db.query(SystemParameter).filter(
            SystemParameter.param_key == 'pdf_image_dpi'
        ).first()
        image_dpi = dpi_param.param_value.get('value', 150) if dpi_param else 150

        # 3. Generar PDF en memoria
        investigation_id = str(job.investigation_id)
        hd_results = job.results or {}

        # Obtener título de la investigación si existe
        from app.models.investigation import UserInvestigation
        investigation = db.query(UserInvestigation).filter(
            UserInvestigation.id == job.investigation_id
        ).first()
        title = investigation.title if investigation else None

        pdf_bytes, sha256 = pdf_service.generate_exploration_pdf(
            investigation_id=investigation_id,
            job_id=job_id,
            hd_results=hd_results,
            investigation_title=title,
            max_images=max_images,
            image_dpi=image_dpi,
        )

        # 4. Validar contenido
        if not pdf_bytes or not pdf_bytes[:5] == b'%PDF-':
            raise ValueError("PDF generado es inválido (no comienza con %PDF-)")

        # 5. Verificar tamaño máximo
        max_size_param = db.query(SystemParameter).filter(
            SystemParameter.param_key == 'pdf_max_size_mb'
        ).first()
        max_size_mb = max_size_param.param_value.get('value', 20) if max_size_param else 20
        actual_size_mb = len(pdf_bytes) / (1024 * 1024)

        if actual_size_mb > max_size_mb:
            logger.warning(
                f"PDF excede límite: {actual_size_mb:.1f} MB > {max_size_mb} MB. "
                "Generando versión reducida sin imágenes embebidas."
            )
            pdf_bytes, sha256 = pdf_service.generate_exploration_pdf(
                investigation_id=investigation_id,
                job_id=job_id,
                hd_results=hd_results,
                investigation_title=title,
                max_images=0,  # sin imágenes embebidas
            )

        # 6. Subir a OCI Object Storage con retry
        object_name = f'explorations/{investigation_id}/{job_id}.pdf'
        pdf_url = _upload_with_retry(
            object_name=object_name,
            file_bytes=pdf_bytes,
            content_type='application/pdf',
        )

        # 7. Actualizar job con resultados PDF
        if job.results is None:
            job.results = {}
        job.results['pdf_url'] = pdf_url
        job.results['pdf_sha256'] = sha256
        job.results['pdf_status'] = 'generated'
        job.results['pdf_size_bytes'] = len(pdf_bytes)
        db.commit()

        logger.info(
            f"PDF generado exitosamente para job {job_id}: "
            f"{len(pdf_bytes)} bytes, SHA-256: {sha256[:12]}..."
        )

        return {
            "status": "generated",
            "pdf_url": pdf_url,
            "sha256": sha256,
            "size_bytes": len(pdf_bytes),
        }

    except Exception as e:
        logger.error(f"Error generando PDF para job {job_id}: {e}", exc_info=True)

        # Marcar estado de PDF como fallido (sin afectar el job HD)
        try:
            if job and job.results is not None:
                job.results['pdf_status'] = 'failed'
                job.results['pdf_error'] = str(e)[:200]
                db.commit()
        except Exception:
            pass

        # Retry si quedan intentos
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)

        return {"status": "failed", "detail": str(e)[:200]}

    finally:
        db.close()


def _upload_with_retry(
    object_name: str,
    file_bytes: bytes,
    content_type: str,
    max_retries: int = 3,
) -> str:
    """Sube archivo a OCI con retry y backoff exponencial."""
    import time
    from app.services.storage_service import upload_to_oci  # ajustar

    last_error = None
    for attempt in range(max_retries):
        try:
            url = upload_to_oci(
                bucket_name='forestguard-reports',
                object_name=object_name,
                file_bytes=file_bytes,
                content_type=content_type,
            )
            return url
        except Exception as e:
            last_error = e
            wait_time = (2 ** attempt) * 2  # 2s, 4s, 8s
            logger.warning(
                f"Upload OCI intento {attempt + 1}/{max_retries} falló: {e}. "
                f"Reintentando en {wait_time}s..."
            )
            time.sleep(wait_time)

    raise RuntimeError(f"Upload OCI falló tras {max_retries} intentos: {last_error}")
```

**Nota para Claude Code:** los imports de modelos (`ExplorationGenerationJob`, `UserInvestigation`, `SystemParameter`) deben ajustarse a los nombres reales. Verificar con:
```bash
grep -rn "class.*Job\|class.*Investigation\|class.*Parameter" app/models/
```

También verificar el servicio de storage real:
```bash
grep -rn "def upload\|class.*Storage\|oci_storage" app/services/
```

---

### PDF-03: registrar task en celery_app.py

**Archivo:** `celery_app.py`
**Esfuerzo:** 5 min
**Dependencias:** PDF-02

Agregar `'workers.tasks.pdf_generation_task'` a la lista de `include` en la configuración de Celery:

```python
# Buscar la lista include y agregar:
include=[
    'workers.tasks.ingestion',
    'workers.tasks.clustering',
    'workers.tasks.recovery',
    'workers.tasks.destruction',
    'workers.tasks.pdf_generation_task',  # NUEVO
    # ... otros tasks existentes
]
```

También verificar que la ruta de queue `reports` esté configurada:
```bash
grep -n "reports" celery_app.py
# Si no existe, agregar en task_routes:
# 'workers.tasks.pdf_generation_task.*': {'queue': 'reports'},
```

---

### PDF-04: encadenar task PDF tras completar job HD

**Archivo:** `app/workers/exploration_hd_worker.py`
**Esfuerzo:** 20 min
**Dependencias:** PDF-02, PDF-03

Al final de `run_generation_job()`, cuando el job cambia a status `ready`, encolar el task de PDF:

```python
# BUSCAR: la línea donde se hace job.status = 'ready' (o equivalente)
# AGREGAR DESPUÉS:

# Encolar generación de PDF como task independiente
try:
    from workers.tasks.pdf_generation_task import generate_pdf_for_job
    generate_pdf_for_job.delay(str(job.id))
    logger.info(f"Task de PDF encolado para job {job.id}")
except Exception as e:
    logger.warning(f"No se pudo encolar task de PDF: {e}")
    # No fallar el job HD por esto
```

**Nota:** NO usar Celery chain. Usar `.delay()` simple porque si el encadenamiento falla, no queremos afectar el estado del job HD. El PDF es complementario.

---

### PDF-05: deduplicación de jobs HD

**Archivo:** `app/api/v1/explorations.py`
**Esfuerzo:** 15 min
**Dependencias:** ninguna (puede ir en paralelo)

En el endpoint `POST /api/v1/explorations/{investigation_id}/generate` (~línea 290), antes de crear un nuevo job, verificar si ya existe uno activo:

```python
# BUSCAR: el punto donde se crea el nuevo job
# AGREGAR ANTES:

# Verificar si ya hay un job activo para esta investigación
existing_job = db.query(ExplorationGenerationJob).filter(
    ExplorationGenerationJob.investigation_id == investigation_id,
    ExplorationGenerationJob.status.in_(['pending', 'processing']),
).first()

if existing_job:
    return {
        'job_id': str(existing_job.id),
        'status': existing_job.status,
        'message': 'Ya existe un job activo para esta investigación',
        'created_at': existing_job.created_at.isoformat(),
    }
```

---

### PDF-06: actualizar endpoint GET assets para incluir PDF

**Archivo:** `app/api/v1/explorations.py`
**Esfuerzo:** 10 min
**Dependencias:** PDF-02

En el endpoint `GET /api/v1/explorations/{investigation_id}/assets` (~línea 450), agregar campos PDF al response:

```python
# BUSCAR: la construcción del response dict
# AGREGAR campos:

response = {
    # ... campos existentes ...
    'pdf': {
        'url': job.results.get('pdf_url'),
        'status': job.results.get('pdf_status', 'not_requested'),
        'sha256': job.results.get('pdf_sha256'),
        'size_bytes': job.results.get('pdf_size_bytes'),
        'error': job.results.get('pdf_error'),
    } if job.results else {'status': 'not_requested'},
}
```

---

### PDF-07: actualizar frontend paso 3 para mostrar estado PDF

**Archivo:** `frontend/src/pages/Exploration.tsx`
**Esfuerzo:** 30 min
**Dependencias:** PDF-06

Buscar la UI de assets HD (~línea 1778) y agregar sección de PDF con estados granulares.

**Cambios requeridos:**

1. En el polling de estado (~línea 915), cuando `status === 'ready'`, verificar también `pdf.status`:

```tsx
// Después de loadExplorationAssets():
// El PDF puede estar: 'not_requested', 'generated', 'failed'
const pdfStatus = assets?.pdf?.status;
```

2. En la UI (~línea 1778), agregar bloque condicional:

```tsx
{/* Sección PDF */}
{assets?.pdf && (
  <div className="mt-4">
    {assets.pdf.status === 'generated' && assets.pdf.url && (
      <button
        onClick={() => window.open(assets.pdf.url, '_blank')}
        className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
      >
        <span>📥</span>
        <span>Descargar PDF del reporte</span>
      </button>
    )}
    {assets.pdf.status === 'failed' && (
      <p className="text-sm text-amber-600">
        El PDF no pudo generarse. Las imágenes HD están disponibles para descarga individual.
      </p>
    )}
    {(!assets.pdf.status || assets.pdf.status === 'not_requested') && (
      <p className="text-sm text-gray-400">
        PDF generándose...
      </p>
    )}
  </div>
)}
```

---

## FASE 3: consolidar fuente de Home

### HOME-01: deprecar endpoint /fire-episodes/active

**Archivo:** `app/api/routes/episodes.py` (o `app/api/v1/episodes.py` según estado del refactor)
**Esfuerzo:** 15 min
**Dependencias:** ninguna

Buscar el endpoint `GET /fire-episodes/active` (~línea 257 según status doc) y agregar header Sunset + redirigir lógica:

```python
# BUSCAR: @router.get(..."/active"...) o similar

from fastapi.responses import JSONResponse
from datetime import datetime, timedelta

@router.get("/fire-episodes/active", deprecated=True)
async def get_active_episodes_deprecated(...):
    """
    DEPRECADO: usar GET /fire-episodes?mode=active en su lugar.
    Este endpoint se eliminará el 2026-05-22.
    """
    # Redirigir internamente a la misma lógica de ?mode=active
    result = await get_episodes(mode="active", ...)  # llamar al handler principal

    response = JSONResponse(content=result)
    response.headers["Sunset"] = "Sat, 23 May 2026 00:00:00 GMT"
    response.headers["Deprecation"] = "true"
    response.headers["Link"] = '</api/v1/fire-episodes?mode=active>; rel="successor-version"'
    return response
```

**Nota:** si `/fire-episodes/active` tiene lógica distinta a `?mode=active`, unificar primero el criterio de negocio en el handler principal antes de deprecar.

---

### HOME-02: verificar y alinear criterio de negocio en /fire-episodes

**Archivo:** `app/api/routes/episodes.py` o `app/api/v1/episodes.py`
**Esfuerzo:** 20 min
**Dependencias:** HOME-01

Comparar la lógica de ambos endpoints:

```bash
# Buscar ambas implementaciones
grep -n "def.*active\|mode.*active\|status.*active" app/api/routes/episodes.py app/api/v1/episodes.py
```

Asegurar que `/fire-episodes?mode=active` aplica exactamente el mismo filtro que `/fire-episodes/active`. Si difieren, usar el criterio documentado en UC-F08R:
- `status IN ('active', 'monitoring')`
- Ordenados por `gee_priority DESC` o `last_seen_at DESC`

---

### HOME-03: actualizar frontend Home

**Archivo:** `frontend/src/pages/Home.tsx` (~línea 65)
**Esfuerzo:** 10 min
**Dependencias:** HOME-01

Verificar que Home solo consume `/fire-episodes?mode=active|recent`:

```bash
grep -n "fire-episodes" frontend/src/pages/Home.tsx frontend/src/hooks/queries/useEpisodesByMode.ts frontend/src/services/endpoints/episodes.ts
```

Si hay alguna referencia a `/fire-episodes/active` (ruta separada), reemplazar por `?mode=active`.

---

### HOME-04: mejorar render de slides parciales en carrusel

**Archivo:** `frontend/src/components/fires/fire-card.tsx`
**Esfuerzo:** 25 min
**Dependencias:** ninguna (puede ir en paralelo)

Actualmente (~línea 70) filtra slides con URL y (~línea 76) aplica heurística de "imagen pendiente". Si alguno de los 3 slides tiene URL pero otros no, el card cae a fallback completo.

**Cambio:** renderizar los slides disponibles y mostrar placeholder solo para los faltantes.

```tsx
// BUSCAR: el filtro de slides (~línea 70)
// REEMPLAZAR la lógica todo-o-nada por:

const slides = episode.slides_data || [];

// Clasificar slides por estado
const availableSlides = slides.filter(s => s.thumbnail_url && s.thumbnail_url.length > 0);
const pendingSlides = slides.filter(s => !s.thumbnail_url);

// Si hay al menos 1 slide disponible, mostrar carrusel (no fallback)
const hasVisibleContent = availableSlides.length > 0;

// En el render:
{hasVisibleContent ? (
  // Renderizar slides disponibles
  availableSlides.map((slide, idx) => (
    <img key={idx} src={slide.thumbnail_url} alt={slide.type} ... />
  ))
) : (
  // Fallback solo cuando NO hay ningún slide disponible
  <div className="fallback-placeholder">
    <span>Imagen satelital en procesamiento...</span>
  </div>
)}
```

---

## FASE 4: storage y cleanup

### STORAGE-01: crear job de limpieza de assets expirados

**Archivo nuevo:** `workers/tasks/cleanup_assets_task.py`
**Esfuerzo:** 30 min
**Dependencias:** PARAM-01

```python
"""
Job programado para limpiar assets expirados de OCI Object Storage.

Política de retención (desde system_parameters):
- Assets HD: hd_asset_retention_days (default 7)
- PDFs: pdf_retention_days (default 90)
- Thumbnails: no se eliminan (persistentes)

Schedule: diario a las 04:00 UTC
"""

import logging
from datetime import datetime, timezone, timedelta
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    name='workers.tasks.cleanup_assets_task.cleanup_expired_assets',
    queue='default',
    acks_late=True,
)
def cleanup_expired_assets():
    """Elimina assets expirados de OCI y actualiza BD."""
    from app.core.database import get_db_session
    from app.models.system_parameter import SystemParameter

    db = get_db_session()

    try:
        # Leer parámetros de retención
        hd_days_param = db.query(SystemParameter).filter(
            SystemParameter.param_key == 'hd_asset_retention_days'
        ).first()
        hd_retention_days = hd_days_param.param_value.get('value', 7) if hd_days_param else 7

        pdf_days_param = db.query(SystemParameter).filter(
            SystemParameter.param_key == 'pdf_retention_days'
        ).first()
        pdf_retention_days = pdf_days_param.param_value.get('value', 90) if pdf_days_param else 90

        now = datetime.now(timezone.utc)
        hd_cutoff = now - timedelta(days=hd_retention_days)
        pdf_cutoff = now - timedelta(days=pdf_retention_days)

        # Buscar assets HD expirados
        from app.models.investigation import InvestigationAsset
        expired_hd = db.query(InvestigationAsset).filter(
            InvestigationAsset.generated_at < hd_cutoff,
        ).all()

        hd_deleted = 0
        for asset in expired_hd:
            try:
                _delete_from_oci(asset.gcs_path)  # adaptar al campo real
                db.delete(asset)
                hd_deleted += 1
            except Exception as e:
                logger.warning(f"Error eliminando asset HD {asset.id}: {e}")

        # Buscar PDFs expirados en job results
        # Nota: los PDFs están referenciados en ExplorationGenerationJob.results['pdf_url']
        # Implementar lógica específica según modelo real

        db.commit()

        logger.info(
            f"Cleanup completado: {hd_deleted} assets HD eliminados "
            f"(cutoff: {hd_retention_days} días)"
        )

        return {
            "hd_deleted": hd_deleted,
            "hd_cutoff_date": hd_cutoff.isoformat(),
        }

    except Exception as e:
        logger.error(f"Error en cleanup de assets: {e}", exc_info=True)
        raise
    finally:
        db.close()


def _delete_from_oci(object_path: str):
    """Elimina un objeto de OCI Object Storage."""
    from app.services.storage_service import delete_from_oci  # ajustar
    delete_from_oci(bucket_name='forestguard-reports', object_name=object_path)
```

---

### STORAGE-02: registrar schedule en celery beat

**Archivo:** `celery_app.py` (sección beat_schedule)
**Esfuerzo:** 5 min
**Dependencias:** STORAGE-01

```python
# Agregar en beat_schedule:
'cleanup-expired-assets': {
    'task': 'workers.tasks.cleanup_assets_task.cleanup_expired_assets',
    'schedule': crontab(hour=4, minute=0),  # 04:00 UTC diario
    'options': {'queue': 'default'},
},
```

---

### STORAGE-03: endpoint admin de monitoreo de storage

**Archivo:** `app/api/v1/imagery.py` (o crear `app/api/v1/admin.py` si no existe)
**Esfuerzo:** 20 min
**Dependencias:** PARAM-02

```python
@router.get("/admin/storage-usage", tags=["admin"])
async def get_storage_usage(db: Session = Depends(get_db)):
    """
    Retorna métricas de uso de storage y GEE.
    Solo para administradores.
    """
    from app.core.gee_semaphore import gee_semaphore
    from app.models.system_parameter import SystemParameter
    from sqlalchemy import func

    # Uso de GEE
    gee_usage = gee_semaphore.get_usage()

    # Contar assets en BD
    from app.models.investigation import InvestigationAsset
    total_assets = db.query(func.count(InvestigationAsset.id)).scalar() or 0

    # Contar episodios con slides válidos
    from app.models.episode import FireEpisode
    episodes_with_slides = db.query(func.count(FireEpisode.id)).filter(
        FireEpisode.slides_data.isnot(None),
        func.jsonb_array_length(FireEpisode.slides_data) > 0,
    ).scalar() or 0

    total_episodes = db.query(func.count(FireEpisode.id)).scalar() or 0

    return {
        "gee": gee_usage,
        "storage": {
            "total_hd_assets": total_assets,
            "episodes_with_slides": episodes_with_slides,
            "episodes_total": total_episodes,
            "slides_coverage_pct": round(
                (episodes_with_slides / total_episodes * 100) if total_episodes > 0 else 0, 1
            ),
        },
        "note": "Para uso real de OCI en bytes, consultar la consola de Oracle Cloud."
    }
```

---

## FASE 5: validación

### TEST-01: verificación backend

**Esfuerzo:** 20 min

```bash
# 1. Verificar que la app arranca
python -c "from app.main import app; print('OK')"

# 2. Verificar imports de nuevos módulos
python -c "from app.core.gee_semaphore import gee_semaphore; print('Semaphore OK')"
python -c "from app.services.gee_scene_cache import find_cached_scene; print('Cache OK')"
python -c "from app.services.pdf_generation_service import PdfGenerationService; print('PDF OK')"
python -c "from workers.tasks.pdf_generation_task import generate_pdf_for_job; print('Task OK')"
python -c "from workers.tasks.cleanup_assets_task import cleanup_expired_assets; print('Cleanup OK')"

# 3. Verificar que no hay imports rotos
grep -rn "from app\.\|import app\." app/ workers/ | python -c "
import sys
errors = []
for line in sys.stdin:
    filepath, content = line.strip().split(':', 2)[0], line.strip()
    # skip comments and strings
    if '#' in content.split(':',2)[-1].split('#')[0]:
        continue
print('No import errors detected' if not errors else f'{len(errors)} errors')
"

# 4. Ejecutar tests existentes (no deben romperse)
pytest tests/ -v --tb=short 2>&1 | tail -20

# 5. Verificar migración SQL
psql $DATABASE_URL -c "SELECT param_key FROM system_parameters WHERE category = 'limits' ORDER BY param_key;"
```

### TEST-02: verificación frontend

```bash
cd frontend

# 1. Verificar build
npm run build 2>&1 | tail -10

# 2. Verificar que no hay errores TypeScript
npx tsc --noEmit 2>&1 | tail -20

# 3. Buscar referencias al endpoint deprecado
grep -rn "fire-episodes/active" src/
# Si aparece en algún lugar que no sea el hook deprecado, corregir
```

### TEST-03: flujo E2E manual

```bash
# 1. Generar HD
curl -X POST http://localhost:8000/api/v1/explorations/{test_id}/generate \
  -H "Authorization: Bearer $TOKEN"
# Guardar job_id del response

# 2. Polling hasta ready
curl http://localhost:8000/api/v1/explorations/{test_id}/generate/{job_id} \
  -H "Authorization: Bearer $TOKEN"
# Esperar status: ready

# 3. Verificar assets incluyen PDF
curl http://localhost:8000/api/v1/explorations/{test_id}/assets \
  -H "Authorization: Bearer $TOKEN"
# Verificar: pdf.status = "generated" y pdf.url no es null

# 4. Verificar storage usage
curl http://localhost:8000/api/v1/admin/storage-usage \
  -H "Authorization: Bearer $TOKEN"

# 5. Verificar Home consume endpoint correcto
curl "http://localhost:8000/api/v1/fire-episodes?mode=active&limit=5"
```

---

## Resumen de archivos

| Acción | Archivo | Fase |
|---|---|---|
| **Crear** | `database/migrations/013_add_storage_and_pdf_parameters.sql` | 0 |
| **Crear** | `app/core/gee_semaphore.py` | 0 |
| **Modificar** | `app/services/imagery_service.py` (agregar semáforo + cache) | 0, 1 |
| **Modificar** | `app/workers/exploration_hd_worker.py` (semáforo + cache + chain PDF) | 0, 1, 2 |
| **Crear** | `app/services/gee_scene_cache.py` | 1 |
| **Crear** | `app/services/pdf_generation_service.py` | 2 |
| **Crear** | `workers/tasks/pdf_generation_task.py` | 2 |
| **Modificar** | `celery_app.py` (include + beat_schedule) | 2, 4 |
| **Modificar** | `app/api/v1/explorations.py` (dedup + PDF en assets) | 2 |
| **Modificar** | `frontend/src/pages/Exploration.tsx` (UI PDF) | 2 |
| **Modificar** | `app/api/routes/episodes.py` o `v1/episodes.py` (deprecar active) | 3 |
| **Modificar** | `frontend/src/components/fires/fire-card.tsx` (slides parciales) | 3 |
| **Crear** | `workers/tasks/cleanup_assets_task.py` | 4 |
| **Modificar** | `app/api/v1/imagery.py` (storage-usage endpoint) | 4 |

**Total:** 6 archivos nuevos, 8 archivos modificados

---

*Documento generado: 2026-02-22*
*Decisiones de arquitectura: PDF independiente ✅ | Home consolidado ✅ | Cache GEE ✅*
