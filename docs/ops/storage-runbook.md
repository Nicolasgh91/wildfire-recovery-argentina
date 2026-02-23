# Storage Runbook — OCI Object Storage en Producción

> Pasos que **no pueden automatizarse en CI** y deben realizarse manualmente por el operador.  
> Los pasos 2 en adelante están cubiertos por el workflow [post-deploy-storage.yml](file:///c:/Users/nicog/wildfire-recovery-argentina/.github/workflows/post-deploy-storage.yml).

---

## PASO 0 — Generar OCI Customer Secret Keys (una sola vez)

> [!IMPORTANT]
> Las **Customer Secret Keys** son el mecanismo S3-compatible de OCI. Son **distintas** a las OCI API Keys (OCID). El Secret Key se muestra **una sola vez** al crearlo.

1. Ir a **OCI Console → Identity → Users → tu usuario → Customer Secret Keys**.
2. Crear una nueva key (botón **Generate Secret Key**).
3. Copiar y guardar en un lugar seguro:
   - **Access Key ID** (se puede volver a ver)
   - **Secret Key** (solo visible al momento de generación)
4. Confirmar que existen los buckets:
   - `forestguard-images`
   - `forestguard-reports`
5. Verificar que el usuario tiene permisos `OBJECT_READ` y `OBJECT_CREATE` sobre esos buckets.

---

## PASO 1 — Editar `.env` en la VM (por cada cambio de credenciales)

```bash
ssh opc@<VM_IP>
nano /home/opc/.env
```

Agregar / corregir las siguientes variables:

```ini
# Storage — OCI (reemplaza la config GCS/MinIO anterior)
STORAGE_BACKEND=oci
OCI_S3_ENDPOINT_URL=https://objectstorage.<REGION>.oci.customer-oci.com
OCI_S3_ACCESS_KEY=<Access Key ID del PASO 0>
OCI_S3_SECRET_KEY=<Secret Key del PASO 0>
OCI_REGION=sa-saopaulo-1
OCI_PUBLIC_URL=

# Entorno
ENVIRONMENT=production
```

> [!CAUTION]
> Eliminar o comentar `STORAGE_PUBLIC_URL=http://127.0.0.1:9000` si está presente.  
> Esa línea es la **causa directa** de las imágenes rotas.

Después de guardar el `.env`, recargar los contenedores para que lean las nuevas vars:

```bash
cd /home/opc
docker compose up -d
```

---

## PASO 2 en adelante — Automatizado vía GitHub Actions

Una vez completados los pasos 0 y 1, ejecutar el workflow:

**GitHub → Actions → Post-Deploy Storage Setup → Run workflow**

| Input | Cuándo activarlo |
|---|---|
| `rebuild_services` | Si cambiaste código de `storage_service.py` o `imagery_service.py` |
| `run_sql_cleanup` | **Solo una vez** tras migrar de MinIO/GCS → OCI. Limpia URLs `127.*` de la DB |
| `run_carousel_regen` | Después de `run_sql_cleanup` para repoblar las slides con URLs OCI |

> [!NOTE]
> El workflow valida automáticamente que las OCI vars estén presentes en el contenedor antes de continuar. Si falló el PASO 1, el step 3 del workflow te avisará con el error exacto.

---

## Endpoint OCI por región

| Región | Endpoint |
|---|---|
| São Paulo (sa-saopaulo-1) | `https://objectstorage.sa-saopaulo-1.oci.customer-oci.com` |
| Ashburn (us-ashburn-1) | `https://objectstorage.us-ashburn-1.oci.customer-oci.com` |
| Frankfurt (eu-frankfurt-1) | `https://objectstorage.eu-frankfurt-1.oci.customer-oci.com` |

---

## Troubleshooting rápido

| Síntoma | Causa probable | Acción |
|---|---|---|
| `"backend": "gcs"` en health check | `STORAGE_BACKEND` no está seteado o vale `gcs` | Editar `.env` → `STORAGE_BACKEND=oci` y `docker compose up -d` |
| `"accessible": false` + error de credencial | Secret Key inválido o expirado | Generar nuevo par en OCI Console (PASO 0) |
| Imágenes siguen cargando desde `127.0.0.1` | `STORAGE_PUBLIC_URL` con valor legacy en `.env` | Eliminar o comentar esa línea |
| `worker-reports` no aparece | docker-compose.yml no incluye el servicio | Verificar que el código de `fix/503-storage-layer` está mergeado a `main` y en la VM |
