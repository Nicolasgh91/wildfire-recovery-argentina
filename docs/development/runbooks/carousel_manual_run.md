## 1) Ejecución Local (Directa / Debugging)

Para probar la lógica sin depender de Celery/Redis:

1.  Asegúrate de tener un archivo `.env` en la raíz con:
    *   `DATABASE_URL`: Conexión a la BD (puede ser tunneling a producción o local).
    *   `GOOGLE_APPLICATION_CREDENTIALS`: Path al JSON de credenciales (o autenticación vía `gcloud auth application-default login`).
    *   `GCS_PROJECT_ID`: ID del proyecto GCP.
    *   `STORAGE_BUCKET_IMAGES`: Bucket de imágenes.

2.  Ejecuta el script:
    ```bash
    python scripts/run_carousel_local.py
    ```

## 2) Ejecución Manual del Task (Celery)

### En Local (con Docker)
1.  Asegúrate que los contenedores estén corriendo (`redis`, `api`, etc.).
2.  Ejecuta el worker si no está corriendo:
    ```bash
    celery -A workers.celery_app worker -l info -Q analysis
    ```
3.  Dispara la tarea:
    ```bash
    celery -A workers.celery_app call workers.tasks.carousel_task.generate_carousel --kwargs='{"force_refresh": true}'
    ```

### En OCI (Producción)
1.  Conéctate a la VM (bastion o directa).
2.  Identifica el contenedor del worker de analysis:
    ```bash
    docker ps | grep analysis
    ```
3.  Ejecuta el comando dentro del contenedor:
    ```bash
    docker exec -it <container_id_or_name> celery -A workers.celery_app call workers.tasks.carousel_task.generate_carousel --kwargs='{"force_refresh": true}'
    ```
    *Ejemplo:*
    ```bash
    docker exec -it forestguard-worker-analysis celery -A workers.celery_app call workers.tasks.carousel_task.generate_carousel --kwargs='{"force_refresh": true}'
    ```

4.  Verifica los logs:
    ```bash
    docker logs --tail 100 -f forestguard-worker-analysis
    ```

## 3) Verificación

### Base de Datos
Verificar si se actualizaron los episodios:
```sql
SELECT count(*) FROM fire_episodes WHERE jsonb_array_length(slides_data) > 0;
```

### Frontend
Visitar la Home y verificar que las tarjetas de incendios activos/recientes muestren el carrusel de imágenes satelitales.

## 4) Regeneración de un episodio individual

Cuando se necesita regenerar los thumbnails de **un solo** episodio sin afectar los
demás, ejecutar este procedimiento desde la VM de producción.

### Paso 1: Limpiar cache del episodio

```bash
docker exec -i forestguard-db psql -U forestguard -d forestguard -c "
  UPDATE fire_episodes
  SET slides_data = NULL,
      last_gee_image_id = NULL,
      slides_status = 'pending'
  WHERE id = '5bd52c45-70c3-43f0-bccf-ccf7be86286c';
"
```

### Paso 2: Disparar regeneración

```bash
docker exec -it forestguard-worker-gee celery -A workers.celery_app call \
  workers.tasks.carousel_task.generate_carousel \
  --kwargs='{"force_refresh": true}' \
  --queue=gee
```

### Paso 3: Verificar logs

```bash
docker logs --tail 50 -f forestguard-worker-gee 2>&1 | grep -i "5bd52c45"
```

### Paso 4: Diagnóstico de brillo post-regeneración

```bash
docker exec -i forestguard-db psql -U forestguard -d forestguard -t -A -c "
  SELECT (slides_data->0->>'thumbnail_url')
  FROM fire_episodes
  WHERE id = '5bd52c45-70c3-43f0-bccf-ccf7be86286c';
" | xargs -I{} sh -c '
  curl -sL "{}" -o /tmp/thumb_check.png && \
  python3 -c "
from PIL import Image
import numpy as np
img = np.array(Image.open(\"/tmp/thumb_check.png\").convert(\"RGB\"), dtype=float)
h, w = img.shape[:2]
size_kb = len(open(\"/tmp/thumb_check.png\",\"rb\").read()) / 1024
left_brightness = img[:, :5, :].mean()
right_brightness = img[:, -5:, :].mean()
ratio = w / h
print(f\"Tamaño: {size_kb:.0f} KB {'✅' if 500 < size_kb < 1200 else '⚠️'}\")
print(f\"Dimensiones: ({w}, {h}) {'✅' if (w,h)==(768,576) else '⚠️'}\")
print(f\"Ratio: {ratio:.4f} {'✅' if abs(ratio-1.3333)<0.01 else '⚠️'}\")
print(f\"Brillo col izquierda: {left_brightness:.2f} {'✅' if left_brightness>10 else '⚠️'}\")
print(f\"Brillo col derecha:   {right_brightness:.2f} {'✅' if right_brightness>10 else '⚠️'}\")
if left_brightness>10 and right_brightness>10:
    print(\"→ SIN FRANJAS NEGRAS ✅\")
else:
    print(\"→ FRANJA NEGRA DETECTADA ⚠️\")
"
'
```

**Criterio de aceptación:**
```
Brillo col izquierda: > 10.0  ✅
Brillo col derecha:   > 10.0  ✅
```

## 5) Causa raíz: franja negra lateral en thumbnails

**Bug:** Algunos thumbnails de episodios pequeños mostraban una franja negra en el borde izquierdo.

**Causa raíz:** La función `_bbox_from_point()` originalmente calculaba un bbox
cuadrado (ratio 1:1). Cuando GEE recibía ese bbox cuadrado y debía generar un
thumbnail de 768×576 (ratio 4:3), rellenaba el espacio horizontal sobrante con
píxeles negros/transparentes.

**Por qué solo afectaba episodios pequeños:** Para episodios geográficamente
grandes, el polígono real supera los límites del canvas y GEE recorta en vez de
rellenar. Para episodios puntuales/chicos, el bbox cuadrado era pequeño y GEE
tenía espacio sobrante → padding negro.

**Fix aplicado:**
- `_bbox_from_point()` en `app/services/imagery_service.py` ahora calcula
  `delta_lon = delta_lat * (width / height)` usando las dimensiones target.
- `_validate_thumbnail()` detecta bandas con brillo medio < 10.0 y loguea warning.
- `create_bbox_from_coordinates()` en `app/utils/bbox_utils.py` requiere
  `aspect_ratio` como parámetro explícito (sin default).

**Validación:** `brillo_col_izquierda > 10.0` y `brillo_col_derecha > 10.0`.

