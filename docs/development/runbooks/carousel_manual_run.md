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
