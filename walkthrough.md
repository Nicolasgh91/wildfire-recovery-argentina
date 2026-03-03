# Walkthrough: Fix Production 503s y URLs rotas

**Rama:** `fix/503-storage-layer` → merge a `main`  
**Fecha:** 2026-02-22  

---

## Qué se implementó (código ya comiteado)

> Nota 2026-03: este walkthrough fue escrito antes de la consolidación de workers en `worker-fast` y `worker-gee`.  
> El diseño actual de contenedores y colas está documentado en `docs/containers/workers.md`.  
> Donde este documento hable de un contenedor dedicado `worker-reports`, hoy la cola `reports` es consumida por `worker-fast`.

| Archivo | Cambio |
|---|---|
| [storage_service.py](file:///c:/Users/nicog/wildfire-recovery-argentina/app/services/storage_service.py) | Backend `oci` vía boto3 S3-compatible |
| [docker-compose.yml](file:///c:/Users/nicog/wildfire-recovery-argentina/docker-compose.yml) | Actualización de workers para usar OCI, colas alineadas con Celery y `ENVIRONMENT` dinámico |
| [.env.template](file:///c:/Users/nicog/wildfire-recovery-argentina/.env.template) | Sección OCI; depreca MinIO/GCS legacy |
| [fix_stale_minio_urls.sql](file:///c:/Users/nicog/wildfire-recovery-argentina/scripts/fix_stale_minio_urls.sql) | Limpia URLs `127.0.0.1:9000` de DB |

---

## Pasos manuales del operador

### PASO 0 — Prerequisitos OCI (si no están listos)

En la consola OCI → **Identity → Users → tu usuario → Customer Secret Keys**:

1. **Generar un Customer Secret Key** (distinto de las OCI API Keys).
2. Copiar el **Access Key ID** y el **Secret Key** (se muestra una sola vez).
3. Confirmar que existen los buckets:
   - `forestguard-images`
   - `forestguard-reports`

> [!IMPORTANT]
> Sin estos valores el paso 1 falla. Las Customer Secret Keys son el mecanismo S3-compatible de OCI, diferentes a las OCID Keys normales.

---

### PASO 1 — Configurar env vars en la VM

Editar `/home/opc/.env` en la VM y agregar/corregir:

```ini
# Storage — OCI (reemplaza la config GCS/MinIO anterior)
STORAGE_BACKEND=oci
OCI_S3_ENDPOINT_URL=https://objectstorage.<REGION>.oci.customer-oci.com
OCI_S3_ACCESS_KEY=<Access Key ID generado en paso 0>
OCI_S3_SECRET_KEY=<Secret Key generado en paso 0>
OCI_REGION=sa-saopaulo-1
OCI_PUBLIC_URL=

# Entorno
ENVIRONMENT=production
```

> [!CAUTION]
> Eliminar o comentar `STORAGE_PUBLIC_URL=http://127.0.0.1:9000` si está presente — esa línea es la causa directa de las imágenes rotas.

---

### PASO 2 — Merge y pull en la VM

```bash
# En local: abrir PR de fix/503-storage-layer → main y mergearlo
# En la VM:
ssh opc@<VM_IP>
cd /home/opc/wildfire-recovery-argentina
git pull origin main
```

---

### PASO 3 — Rebuild y restart de contenedores

```bash
# Rebuild de servicios relevantes para storage y reportes
docker compose build --no-cache api worker-fast worker-gee

# Levantar todo
docker compose up -d

# Verificar que los workers principales están corriendo
docker compose ps | grep worker-fast
```

Resultado esperado:
```
forestguard-worker-fast   running   ...
```

---

### PASO 4 — Aplicar script SQL de limpieza (BUG-3)

```bash
# Opción A: desde el contenedor api (si tiene psql)
docker compose exec api psql "$DATABASE_URL" -f scripts/fix_stale_minio_urls.sql

# Opción B: desde la VM directamente
psql "$DATABASE_URL" -f /home/opc/wildfire-recovery-argentina/scripts/fix_stale_minio_urls.sql
```

El script imprime conteos antes y después. Ambas columnas del "después" deben ser **0**.

---

### PASO 5 — Verificar health del storage

```bash
docker compose exec api python -c "
from app.services.storage_service import StorageService
s = StorageService()
print(s.health_check())
"
```

Resultado esperado:
```json
{"status": "healthy", "backend": "oci", "bucket": "forestguard-images", "accessible": true, ...}
```

> [!NOTE]
> Si aparece `"backend": "gcs"` o un error de credenciales, verificar que las env vars del paso 1 estén cargadas (`docker compose exec api env | grep OCI`).

---

### PASO 6 — Regenerar thumbnails del carrusel

Las slides_data de los episodios quedaron vacíos tras el script SQL. Este comando los regenera con URLs OCI:

```bash
docker compose exec api python -c "
from app.db.session import SessionLocal
from app.services.imagery_service import ImageryService
db = SessionLocal()
svc = ImageryService(db)
result = svc.run_carousel(max_fires=20, force_refresh=True)
print(result)
db.close()
"
```

Resultado esperado: `{"processed": N, "updated": N, "skipped": ..., "errors": []}`

---

## Verificaciones finales

| Check | Comando / acción | Esperado |
|---|---|---|
| **V-01 Storage** | Paso 5 | `"backend": "oci"`, `"status": "healthy"` |
| **V-02 Reports** | `curl -X POST .../reports/judicial -H "Authorization: Bearer <token>"` | 200 con `pdf_url`, **no 503** |
| **V-03 Explorations** | `curl -X POST .../explorations/<id>/generate -H "Idempotency-Key: ..."` | 202 Accepted, **no 503** |
| **V-04 DB limpia** | `SELECT COUNT(*) FROM satellite_images WHERE thumbnail_url LIKE 'http://127%'` | 0 |
| **V-05 Workers Celery** | `docker compose ps \| grep worker-fast` | `running` |
| **V-06 Browser** | Abrir Home, DevTools → Network | Imágenes cargan desde URLs OCI, no `127.0.0.1` |

---

## Rollback (si algo falla)

```bash
# Revertir al commit anterior en la VM
git revert HEAD
docker compose up -d
```

Los datos en DB no se revierten automáticamente, pero el script SQL es seguro (nullifica URLs, no elimina filas).
