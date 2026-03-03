## Core Preproceso de Imágenes — Runbook de troubleshooting

Guía rápida para incidentes relacionados con thumbnails, watermarks y PNG corruptos.

### Escenario 1: Thumbnails no cargan en el carrusel (URLs 404 o vacías)

**Síntomas**:

- En la home no se muestran imágenes para determinados episodios.
- Inspeccionando `slides_data`, hay URLs vacías o inexistentes.

**Pasos**:

1. Verificar en BD:

```sql
SELECT id, status, gee_candidate,
       jsonb_array_length(slides_data) AS slides
FROM fire_episodes
WHERE id = '<EPISODE_ID>';
```

2. Si `slides = 0` o `slides_data IS NULL`:
   - Regenerar el episodio con el script canónico (ver manual):

```bash
docker exec forestguard-api python scripts/regenerate_fixed_episode.py
```

3. Revisar logs de GEE (`ImageryService`) para ese episodio si la regeneración falla.

### Escenario 2: PNG se ve corrupto o con franjas negras

**Síntomas**:

- Imágenes que se muestran con bordes negros o artefactos.
- Errores de PIL al intentar abrir/guardar.

**Pasos**:

1. Probar integridad usando el comando del `watermark_debugging_guide.md`:

```bash
docker exec forestguard-api python -c "
import urllib.request
from PIL import Image
import io

url = 'URL_DE_LA_IMAGEN'
with urllib.request.urlopen(url) as r:
    data = r.read()
img = Image.open(io.BytesIO(data))
print(img.size, img.mode)
"
```

2. Si falla el `save()` o se detecta franja negra:
   - Revisar `PNG_CORRUPTION_FIX_SUMMARY.md` para entender el patrón.
   - Regenerar el episodio usando el script de fix/regeneración.

### Escenario 3: Necesidad de desactivar watermark temporalmente

**Objetivo**: aislar si el watermark es la causa de la corrupción.

**Pasos**:

1. Configurar feature flags en el entorno:

```bash
DISABLE_WATERMARK_LOGO=true          # desactiva solo logo
# o
DISABLE_WATERMARK_ALL=true          # desactiva todo el watermark
```

2. Regenerar un episodio de prueba:

```bash
docker exec forestguard-api python scripts/regenerate_episode_no_watermark.py EPISODE_ID --disable-all
```

3. Volver a probar integridad de la imagen.
4. Si la versión sin watermark es limpia, revisar `app/utils/watermark.py` y mantener la flag activa hasta desplegar un fix.

### Escenario 4: Scripts mencionados en docs que no existen o se movieron

**Síntomas**:

- La guía hace referencia a `scripts/diagnose_png_corruption.py` o `deep_png_fix.py` y el archivo no se encuentra.

**Pasos**:

1. Usar las pruebas directas descritas arriba (`PIL` + URLs).
2. Priorizar los scripts efectivamente presentes (`regenerate_fixed_episode.py`, `regenerate_episode_no_watermark.py`).
3. Actualizar la documentación local de equipo para reflejar la ubicación real de utilidades si se reintroducen.

### Escenario 5: Validación final tras un fix masivo

1. Ejecutar consultas de muestra:

```sql
SELECT COUNT(*) AS total, 
       COUNT(*) FILTER (WHERE slides_data IS NOT NULL AND jsonb_array_length(slides_data) = 3) AS con_3_slides
FROM fire_episodes
WHERE gee_candidate;
```

2. Navegar la home y confirmar que:
   - no hay tarjetas sin imagen,
   - las imágenes tienen proporción 4:3,
   - no hay bordes negros evidentes.

Para decisiones arquitectónicas y parámetros, ver también `core-preproceso-design.md` y `PNG_CORRUPTION_FIX_SUMMARY.md`.

