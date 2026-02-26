# Verificación de credenciales para el carrusel (worker-gee)

Este documento lista todas las credenciales y variables de entorno que usa el flujo de generación de thumbnails del carrusel, dónde se usan y cómo comprobar en la VM que están cargadas (sin exponer valores sensibles).

---

## 1. Base de datos (Supabase)

| Variable       | Uso                    | Cómo verificar en la VM |
|----------------|------------------------|---------------------------|
| `DB_HOST`      | Conexión a PostgreSQL   | `docker exec forestguard-worker-gee env \| grep -E '^DB_' \| sed 's/=.*/=***/'` — deben aparecer DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD (valor oculto). |
| `DB_PORT`      | Puerto DB              | Idem. |
| `DB_NAME`      | Nombre de la base      | Idem. |
| `DB_USER`      | Usuario                | Idem. |
| `DB_PASSWORD`  | Contraseña             | Idem. |

**Comprobar conectividad:** Si la API está healthy, la DB suele estar bien. Desde la VM: `curl -s http://localhost:8000/health/ready` debe devolver `{"ready":true}`.

---

## 2. Redis (Celery broker)

| Variable               | Uso              | Cómo verificar en la VM |
|------------------------|------------------|---------------------------|
| `CELERY_BROKER_URL`    | Cola de tareas   | `docker exec forestguard-worker-gee env \| grep CELERY_BROKER` → debe ser `redis://redis:6379/0` (o similar). |
| `CELERY_RESULT_BACKEND`| Resultados       | `docker exec forestguard-worker-gee env \| grep CELERY_RESULT` → típicamente `redis://redis:6379/1`. |

**Comprobar:** Los logs del worker muestran "Connected to redis://...". Si los workers arrancan, Redis está bien.

---

## 3. Google Earth Engine (GEE)

| Variable                    | Uso                         | Cómo verificar en la VM |
|-----------------------------|-----------------------------|---------------------------|
| `GEE_PROJECT_ID`            | Proyecto GCP con Earth Engine | `docker exec forestguard-worker-gee env \| grep GEE_PROJECT` → no vacío. |
| `GEE_SERVICE_ACCOUNT_EMAIL` | Cuenta de servicio          | `docker exec forestguard-worker-gee env \| grep GEE_SERVICE_ACCOUNT_EMAIL` → no vacío. |
| `GEE_PRIVATE_KEY_PATH`      | Ruta al JSON de la key      | `docker exec forestguard-worker-gee env \| grep GEE_PRIVATE_KEY_PATH` → ej. `/run/secrets/gee-service-account.json`. |
| Archivo en `/run/secrets/`  | Contenido del JSON          | `docker exec forestguard-worker-gee test -f /run/secrets/gee-service-account.json && echo "EXISTS" || echo "MISSING"`. No hacer cat del archivo (es secreto). |

**Comprobar:** En los logs del carousel aparece "GEE autenticado con credenciales de service account + key path". Si hay `GEEImageNotFoundError` pero no "credentials", GEE está cargado; el error es por falta de imagen satelital válida.

---

## 4. OCI Object Storage (subida de thumbnails)

Estas son las que fallaron con `NoSuchBucket` para el bucket `forestguard-images`.

| Variable                 | Uso                              | Cómo verificar en la VM |
|--------------------------|-----------------------------------|---------------------------|
| `STORAGE_BACKEND`        | Backend activo (debe ser `oci`)   | `docker exec forestguard-worker-gee env \| grep STORAGE_BACKEND` → `oci`. |
| `STORAGE_BUCKET_IMAGES`  | Nombre del bucket de imágenes    | `docker exec forestguard-worker-gee env \| grep STORAGE_BUCKET_IMAGES` → debe ser el **nombre exacto** del bucket que existe en tu tenancy OCI (ej. `forestguard-images`). Si está vacío, el código usa por defecto `forestguard-images`. |
| `OCI_S3_ENDPOINT_URL`    | Endpoint S3-compatible de OCI     | `docker exec forestguard-worker-gee env \| grep OCI_S3_ENDPOINT` → no vacío (ej. `https://objectstorage.sa-saopaulo-1.oraclecloud.com`). |
| `OCI_S3_ACCESS_KEY`      | Access key (API key OCI)          | `docker exec forestguard-worker-gee env \| grep OCI_S3_ACCESS_KEY \| sed 's/=.*/=***/'` → debe existir y no estar vacío. |
| `OCI_S3_SECRET_KEY`      | Secret key                        | Idem con `OCI_S3_SECRET_KEY`. |
| `OCI_REGION`             | Región (ej. sa-saopaulo-1)        | `docker exec forestguard-worker-gee env \| grep OCI_REGION`. |
| `OCI_PUBLIC_URL` / `STORAGE_PUBLIC_URL` | Base URL pública de los objetos (opcional) | Para que las URLs en `slides_data` sean accesibles desde el front. |

**Causa típica de NoSuchBucket:**

- El bucket **no existe** en el compartment/namespace de la tenancy OCI a la que apuntan las credenciales. En la consola OCI: Object Storage → verificar que existe un bucket con el **mismo nombre** que `STORAGE_BUCKET_IMAGES`.
- Las credenciales (API Key de usuario OCI o customer secret key) pertenecen a **otra tenancy** o a un usuario que **no tiene permisos** sobre ese bucket. Verificar en IAM que el usuario/group tenga política que permita `objectstorage-object-create` (y list/read) en el compartment del bucket.

**Comprobar que el bucket existe y es accesible:** Desde la VM, con las mismas env del worker, se puede hacer un put de prueba (o usar el endpoint `/health` si en el futuro se añade un check de storage OCI). Por ahora la comprobación es manual en la consola OCI.

---

## 5. Resumen: checklist en la VM

Ejecutar en la VM (por ejemplo tras `cd` al directorio del proyecto o donde esté el compose):

```bash
echo "=== 1. Variables DB (solo nombres) ==="
docker exec forestguard-worker-gee env | grep -E '^DB_' | cut -d= -f1

echo "=== 2. CELERY (broker/backend) ==="
docker exec forestguard-worker-gee env | grep CELERY_ | sed 's/=.*/=***/'

echo "=== 3. GEE (solo nombres) ==="
docker exec forestguard-worker-gee env | grep -E '^GEE_' | cut -d= -f1

echo "=== 4. GEE key file exists? ==="
docker exec forestguard-worker-gee test -f /run/secrets/gee-service-account.json && echo "GEE key file: EXISTS" || echo "GEE key file: MISSING"

echo "=== 5. Storage / OCI (solo nombres, valores ocultos) ==="
docker exec forestguard-worker-gee env | grep -E '^STORAGE_|^OCI_' | sed 's/=.*/=***/'

echo "=== 6. Bucket name (valor visible para verificar nombre exacto) ==="
docker exec forestguard-worker-gee env | grep STORAGE_BUCKET_IMAGES
```

- Si alguna variable necesaria no aparece o está vacía, falta cargarla en el `.env` o en el `environment` del servicio en docker-compose (o en el sistema de secrets que use el deploy).
- Si `STORAGE_BUCKET_IMAGES` tiene un valor distinto al nombre del bucket en OCI, corregir la variable o crear el bucket con ese nombre en OCI.

---

## Referencia rápida de archivos

- **Lectura de env / defaults:** [app/services/storage_service.py](app/services/storage_service.py) (BUCKETS, backend OCI), [app/services/gee_service.py](app/services/gee_service.py) (GEE), [app/core/config.py](app/core/config.py) (Settings).
- **Variables en contenedores:** [docker-compose.yml](docker-compose.yml) — servicio `worker-gee` (environment).
