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
2.  Identifica el contenedor del worker GEE:
    ```bash
    docker ps | grep worker-gee
    ```
3.  Ejecuta el comando dentro del contenedor:
    ```bash
    docker exec -it forestguard-worker-gee celery -A workers.celery_app call workers.tasks.carousel_task.generate_carousel --kwargs='{"force_refresh": true}'
    ```

4.  Verifica los logs:
    ```bash
    docker logs --tail 100 -f forestguard-worker-gee
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

> La base de datos es remota (no hay contenedor `forestguard-db`).
> Se ejecuta el SQL desde `forestguard-api`, que tiene conectividad a la BD vía `DB_HOST`.

```bash
docker exec -i forestguard-api python -c "
import os, sqlalchemy
engine = sqlalchemy.create_engine(os.environ['DATABASE_URL'])
with engine.begin() as conn:
    r = conn.execute(sqlalchemy.text(\"""
        UPDATE fire_episodes
        SET slides_data = NULL,
            last_gee_image_id = NULL,
            slides_status = 'pending'
        WHERE id = '5bd52c45-70c3-43f0-bccf-ccf7be86286c'
    \"""))
    print(f'Rows updated: {r.rowcount}')
"
```

### Paso 2: Disparar regeneración

> `generate_carousel` procesa todos los episodios prioritarios en batch, pero
> como el Paso 1 solo limpió el cache del episodio target, todos los demás
> recibirán cache hit y serán salteados. Solo se regenera el episodio limpiado.
>
> **Importante:** `worker-gee` escucha las colas `analysis` y `vae`. Aunque
> `task_routes` en `celery_app.py` enruta `generate_carousel` a la cola `gee`,
> esa cola no tiene consumidor activo. Se debe forzar `--queue=analysis`.

```bash
docker exec -it forestguard-worker-gee celery -A workers.celery_app call \
  workers.tasks.carousel_task.generate_carousel \
  --kwargs='{"force_refresh": true}' \
  --queue=analysis
```

### Paso 3: Verificar logs

```bash
docker logs --tail 50 -f forestguard-worker-gee 2>&1 | grep -i "5bd52c45"
```

### Paso 4: Diagnóstico de brillo post-regeneración

> Se ejecuta desde la VM host. Primero se obtiene la URL del thumbnail
> vía el contenedor API y luego se descarga y analiza localmente.

```bash
# Obtener la URL del thumbnail
THUMB_URL=$(docker exec -i forestguard-api python -c "
import os, sqlalchemy, json
engine = sqlalchemy.create_engine(os.environ['DATABASE_URL'])
with engine.connect() as conn:
    row = conn.execute(sqlalchemy.text(\"""
        SELECT slides_data->0->>'thumbnail_url'
        FROM fire_episodes
        WHERE id = '5bd52c45-70c3-43f0-bccf-ccf7be86286c'
    \""")).scalar()
    print(row or '')
")

# Descargar y analizar
curl -sL "$THUMB_URL" -o /tmp/thumb_check.png

docker exec -i forestguard-api python -c "
from PIL import Image
import numpy as np
img = np.array(Image.open('/tmp/thumb_check.png').convert('RGB'), dtype=float)
h, w = img.shape[:2]
import os
size_kb = os.path.getsize('/tmp/thumb_check.png') / 1024
left_brightness = img[:, :5, :].mean()
right_brightness = img[:, -5:, :].mean()
ratio = w / h
print(f'Tamaño: {size_kb:.0f} KB {chr(9989) if 500 < size_kb < 1200 else chr(9888)}')
print(f'Dimensiones: ({w}, {h}) {chr(9989) if (w,h)==(768,576) else chr(9888)}')
print(f'Ratio: {ratio:.4f} {chr(9989) if abs(ratio-1.3333)<0.01 else chr(9888)}')
print(f'Brillo col izquierda: {left_brightness:.2f} {chr(9989) if left_brightness>10 else chr(9888)}')
print(f'Brillo col derecha:   {right_brightness:.2f} {chr(9989) if right_brightness>10 else chr(9888)}')
if left_brightness>10 and right_brightness>10:
    print('-> SIN FRANJAS NEGRAS ' + chr(9989))
else:
    print('-> FRANJA NEGRA DETECTADA ' + chr(9888))
"
```

> **Nota:** El paso de análisis requiere que `/tmp/thumb_check.png` esté accesible
> dentro del contenedor. Alternativamente, copia el archivo al contenedor con
> `docker cp /tmp/thumb_check.png forestguard-api:/tmp/thumb_check.png` antes de
> ejecutar el script de Python.

**Criterio de aceptación:**
```
Brillo col izquierda: > 10.0  ✅
Brillo col derecha:   > 10.0  ✅
```

## 5) Causa raíz: franja negra lateral en thumbnails

**Bug:** Algunos thumbnails de episodios pequeños mostraban una franja negra en el borde izquierdo.

### Capa 1 — bbox con aspect ratio incorrecto (fix anterior)

**Causa:** La función `_bbox_from_point()` originalmente calculaba un bbox
cuadrado (ratio 1:1). Cuando GEE recibía ese bbox cuadrado y debía generar un
thumbnail de 768×576 (ratio 4:3), rellenaba el espacio horizontal sobrante con
píxeles negros/transparentes.

**Por qué solo afectaba episodios pequeños:** Para episodios geográficamente
grandes, el polígono real supera los límites del canvas y GEE recorta en vez de
rellenar. Para episodios puntuales/chicos, el bbox cuadrado era pequeño y GEE
tenía espacio sobrante → padding negro.

**Fix:**
- `_bbox_from_point()` en `app/services/imagery_service.py` ahora calcula
  `delta_lon = delta_lat * (width / height)` usando las dimensiones target.
- `_validate_thumbnail()` detecta bandas con brillo medio < 10.0 y loguea warning.
- `create_bbox_from_coordinates()` en `app/utils/bbox_utils.py` requiere
  `aspect_ratio` como parámetro explícito (sin default).

### Capa 2 — `getThumbURL` con `dimensions="WxH"` no garantiza canvas exacto (fix actual)

**Causa raíz real:** `getThumbURL` interpreta el parámetro `dimensions` como
"tamaño máximo del eje más largo" y ajusta el otro eje según el AR de la geometría
proyectada. Cualquier error de punto flotante en la proyección geodésica del bbox
(aunque el AR del bbox en grados sea exactamente 4:3) causa que GEE rellene el
canvas con píxeles negros.

**Por qué el fix de Capa 1 fue necesario pero insuficiente:** Un bbox en grados
con AR 4:3 no produce un raster GEE con AR 4:3 exacto debido a la proyección
geodésica. La diferencia, aunque mínima, es suficiente para que `dimensions="WxH"`
introduzca padding.

**Fix aplicado:** En `get_thumbnail_url()` de `app/services/gee_service.py`,
si `dimensions` es una cadena `"WxH"`, se parsea y se pasan `width` y `height`
como enteros separados a `getThumbURL`. Con `width`+`height` explícitos, GEE
produce exactamente el canvas solicitado sin padding.

```python
# Antes (no garantizaba canvas exacto):
url = vis_image.getThumbURL({"region": geometry, "dimensions": "768x576", ...})

# Después (canvas exacto):
url = vis_image.getThumbURL({"region": geometry, "width": 768, "height": 576, ...})
```

Entradas `int`, `float` o string numérico (ej. `512`, `"512"`, `"512.0"`) mantienen
el comportamiento legacy usando el parámetro `dimensions` como eje mayor.

**Validación:** `brillo_col_izquierda > 10.0` y `brillo_col_derecha > 10.0`.

---

## 6) Regeneración y verificación en producción (episodio individual)

Bloque bash listo para ejecutar en la VM. Usa las variables de entorno del
contenedor (`DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, `DB_NAME`).

```bash
EPISODE_ID="5bd52c45-70c3-43f0-bccf-ccf7be86286c"

# Paso 1: Limpiar cache del episodio
docker exec -i forestguard-api python -c "
import os, sqlalchemy
url = 'postgresql+psycopg2://{user}:{pw}@{host}:{port}/{db}'.format(
    user=os.environ['DB_USER'],
    pw=os.environ['DB_PASSWORD'],
    host=os.environ['DB_HOST'],
    port=os.environ.get('DB_PORT', '5432'),
    db=os.environ['DB_NAME'],
)
engine = sqlalchemy.create_engine(url)
with engine.begin() as conn:
    r = conn.execute(sqlalchemy.text('''
        UPDATE fire_episodes
        SET slides_data = NULL,
            last_gee_image_id = NULL,
            slides_status = 'pending'
        WHERE id = '$EPISODE_ID'
    '''))
    print(f'Rows updated: {r.rowcount}')
"

# Paso 2: Disparar regeneración (solo re-procesa episodios sin cache)
docker exec -it forestguard-worker-gee celery -A workers.celery_app call \
  workers.tasks.carousel_task.generate_carousel \
  --kwargs='{"force_refresh": true}' \
  --queue=analysis

# Paso 3: Monitorear logs filtrados por UUID del episodio
docker logs --tail 50 -f forestguard-worker-gee 2>&1 | grep -i "$EPISODE_ID"

# Paso 4: Diagnóstico de brillo post-regeneración
THUMB_URL=$(docker exec -i forestguard-api python -c "
import os, sqlalchemy, json
url = 'postgresql+psycopg2://{user}:{pw}@{host}:{port}/{db}'.format(
    user=os.environ['DB_USER'],
    pw=os.environ['DB_PASSWORD'],
    host=os.environ['DB_HOST'],
    port=os.environ.get('DB_PORT', '5432'),
    db=os.environ['DB_NAME'],
)
engine = sqlalchemy.create_engine(url)
with engine.connect() as conn:
    row = conn.execute(sqlalchemy.text(\"""
        SELECT slides_data->0->>'thumbnail_url'
        FROM fire_episodes
        WHERE id = '$EPISODE_ID'
    \""")).scalar()
    print(row or '')
")

curl -sL "$THUMB_URL" -o /tmp/thumb_check.png

docker exec -i forestguard-api python -c "
from PIL import Image
import numpy as np
img = np.array(Image.open('/tmp/thumb_check.png').convert('RGB'), dtype=float)
h, w = img.shape[:2]
import os
size_kb = os.path.getsize('/tmp/thumb_check.png') / 1024
left_brightness = img[:, :5, :].mean()
right_brightness = img[:, -5:, :].mean()
ratio = w / h
print(f'Tamaño: {size_kb:.0f} KB {chr(9989) if 500 < size_kb < 1200 else chr(9888)}')
print(f'Dimensiones: ({w}, {h}) {chr(9989) if (w,h)==(768,576) else chr(9888)}')
print(f'Ratio: {ratio:.4f} {chr(9989) if abs(ratio-1.3333)<0.01 else chr(9888)}')
print(f'Brillo col izquierda: {left_brightness:.2f} {chr(9989) if left_brightness>10 else chr(9888)}')
print(f'Brillo col derecha:   {right_brightness:.2f} {chr(9989) if right_brightness>10 else chr(9888)}')
if left_brightness>10 and right_brightness>10:
    print('-> SIN FRANJAS NEGRAS ' + chr(9989))
else:
    print('-> FRANJA NEGRA DETECTADA ' + chr(9888))
"
```

> **Nota:** El paso de análisis requiere que `/tmp/thumb_check.png` esté accesible
> dentro del contenedor. Alternativamente, copia el archivo al contenedor con
> `docker cp /tmp/thumb_check.png forestguard-api:/tmp/thumb_check.png` antes de
> ejecutar el script de Python.

**Criterio de aceptación:**
```
Brillo col izquierda: > 10.0  ✅
Brillo col derecha:   > 10.0  ✅
```

