# 🔍 Reporte Técnico: Workers ↔ GCS Connectivity Diagnostic

**Fecha:** 2026-02-09  
**Autor:** Cloud Infrastructure Engineer & Backend Developer  
**Versión:** 1.0

---

## Resumen Ejecutivo

Se auditó la conectividad entre los Celery Workers locales y Google Cloud Storage (GCS). Se encontraron **7 puntos de falla** que impiden la comunicación. El más crítico: **`STORAGE_BACKEND=local`** en el `.env` raíz, forzando a todos los workers a escribir al filesystem local en vez de GCS.

### Archivos Auditados

| Archivo | Propósito |
|---------|-----------|
| `celery_app.py` (root) | Config Celery (4 tasks) |
| `workers/celery_app.py` | Config Celery (8 tasks) — usado por Docker |
| `app/services/gcs_service.py` | Cliente GCS con ADC (Singleton) |
| `app/services/storage_service.py` | Storage multi-backend: gcs/r2/local |
| `app/workers/exploration_hd_worker.py` | Worker HD images → StorageService |
| `app/services/closure_report_service.py` | Closure reports → StorageService |
| `app/services/imagery_service.py` | Carousel thumbnails → StorageService |
| `workers/tasks/ingestion.py` | Ingesta FIRMS (sin GCS) |
| `workers/tasks/carousel_task.py` | Task Celery → ImageryService |
| `workers/tasks/closure_report_task.py` | Task Celery → ClosureReportService |
| `docker-compose.yml` | Orquestación de servicios |
| `Dockerfile.worker` | Imagen Docker para workers |
| `.env` (root) | Variables de entorno desarrollo |
| `docker/.env` | Variables de entorno Docker |

---

## 1. Arquitectura de Storage Actual

```
┌─────────────────────────────────────────────────────────────────────┐
│                    WORKER → STORAGE FLOW                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐              │
│  │ worker-     │   │ worker-     │   │ worker-     │              │
│  │ ingestion   │   │ clustering  │   │ analysis    │               │
│  └──────┬──────┘   └──────┬──────┘   └──────┬──────┘               │
│         │                  │                 │                      │
│         │ (no GCS)         │ (no GCS)        │                      │
│         │                  │                 ├── carousel_task      │
│         ▼                  ▼                 ├── closure_report     │
│    ┌─────────┐       ┌─────────┐             ├── exploration_hd     │
│    │  DB     │       │  DB     │             │                      │
│    │  only   │       │  only   │             ▼                      │
│    └─────────┘       └─────────┘       ┌─────────────┐             │
│                                        │ Storage     │             │
│                                        │ Service     │             │
│                                        │ (backend?)  │             │
│                                        └──────┬──────┘             │
│                                ┌──────────────┼──────────────┐     │
│                                ▼              ▼              ▼     │
│                         ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│                         │ local ⚠️ │  │ gcs ✅   │  │ r2       │  │
│                         │./storage/│  │ Buckets  │  │ (legacy) │  │
│                         └──────────┘  └──────────┘  └──────────┘  │
│                              ↑                                     │
│                    ┌─────────┘                                     │
│                    │ ACTUALMENTE ACTIVO                             │
│                    │ STORAGE_BACKEND=local                          │
│                    └───────────────────                             │
│                                                                      │
│  ┌─────────────┐                                                   │
│  │ GCSService  │ ← Singleton, NO usado por workers                 │
│  │ (legacy)    │   Crashea en import si falta GCS_PROJECT_ID       │
│  └─────────────┘                                                   │
│                                                                      │
│  GCS BUCKETS TARGET:                                                │
│  ┌─────────────────────┐  ┌──────────────────┐  ┌─────────────────┐│
│  │ forestguard-images  │  │ forestguard-     │  │ forestguard-    ││
│  │ (thumbnails, HD,    │  │ reports          │  │ certificates    ││
│  │  capas satelitales) │  │ (cierre, evid.)  │  │ (auditoría)     ││
│  └─────────────────────┘  └──────────────────┘  └─────────────────┘│
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

> **IMPORTANTE:** Los workers usan `StorageService` (no `GCSService`). `StorageService` soporta 3 backends: `gcs`, `r2`, `local`. Actualmente el `.env` lo configura como `local`.

---

## 2. Puntos de Falla Encontrados

### ❌ PF-1: `STORAGE_BACKEND=local` en `.env` raíz (CRÍTICO)

| Campo | Detalle |
|-------|---------|
| **Archivo** | `.env` línea 108 |
| **Contenido** | `STORAGE_BACKEND=local #gcs` |
| **Impacto** | **Todos los workers escriben al filesystem local `./storage/`, NO a GCS** |
| **Fix** | Cambiar a `STORAGE_BACKEND=gcs` |

```diff
-STORAGE_BACKEND=local #gcs
+STORAGE_BACKEND=gcs
```

---

### ❌ PF-2: `GOOGLE_APPLICATION_CREDENTIALS` comentado en `.env`

| Campo | Detalle |
|-------|---------|
| **Archivo** | `.env` línea 112 |
| **Contenido** | `#GOOGLE_APPLICATION_CREDENTIALS="C:\ruta\absoluta\service-account-gcs.json"` |
| **Impacto** | Sin credenciales explícitas, `StorageService` falla al crear el cliente GCS |
| **Fix** | Descomentar y apuntar a la ruta del SA JSON, o usar ADC (`gcloud auth application-default login`) |

```diff
-#GOOGLE_APPLICATION_CREDENTIALS="C:\ruta\absoluta\service-account-gcs.json"
+GOOGLE_APPLICATION_CREDENTIALS=C:\Users\nicog\.config\gcloud\application_default_credentials.json
```

**Alternativa recomendada:** Ejecutar `gcloud auth application-default login` una vez y el SDK detecta credenciales automáticamente.

---

### ❌ PF-3: `gcs_service.py` Singleton crash at import

| Campo | Detalle |
|-------|---------|
| **Archivo** | `app/services/gcs_service.py` línea 395 |
| **Contenido** | `gcs_service = GCSService()` |
| **Impacto** | Cualquier `import` de este módulo crashea si `GCS_PROJECT_ID` no está definido → `ValueError` inmediato |

> **NOTA:** Este servicio NO es usado por los workers (usan `StorageService`), pero cualquier import transitivo puede causar crash en toda la aplicación.

```diff
 # Singleton global
-gcs_service = GCSService()
+# Lazy initialization to avoid crashes on import
+gcs_service = None
+
+def get_gcs_service() -> GCSService:
+    global gcs_service
+    if gcs_service is None:
+        gcs_service = GCSService()
+    return gcs_service
```

---

### ⚠️ PF-4: Dos `celery_app.py` con listas de tasks divergentes

| Campo | Detalle |
|-------|---------|
| **Archivos** | `celery_app.py` (root) vs `workers/celery_app.py` |
| **Diferencia** | Root tiene **4 tasks**; `workers/` tiene **8 tasks** (incluye `carousel_task`, `closure_report_task`, `episode_merge_task`, `clustering_task`) |
| **Impacto** | Docker usa `workers.celery_app` (correcto), pero desarrollo local puede apuntar al root |
| **Fix** | Eliminar `celery_app.py` del root o sincronizar |

---

### ⚠️ PF-5: Docker user home path mismatch

| Campo | Detalle |
|-------|---------|
| **Archivo** | `docker-compose.yml` línea 53, 88, 127, 160 |
| **Contenido** | Monta en `/home/user/.config/gcloud/` |
| **Problema** | `Dockerfile.worker` crea usuario **`celery`** (no `user`). Path correcto: `/home/celery/.config/gcloud/` |

```diff
 environment:
-  GOOGLE_APPLICATION_CREDENTIALS: /home/user/.config/gcloud/application_default_credentials.json
+  GOOGLE_APPLICATION_CREDENTIALS: /home/celery/.config/gcloud/application_default_credentials.json
 volumes:
-  - ~/.config/gcloud:/home/user/.config/gcloud:ro
+  - ~/.config/gcloud:/home/celery/.config/gcloud:ro
```

---

### ⚠️ PF-6: Workers faltantes de `STORAGE_BUCKET_*` en docker-compose

| Campo | Detalle |
|-------|---------|
| **Archivo** | `docker-compose.yml` líneas 74-179 |
| **Problema** | Solo el servicio `api` tiene `STORAGE_BUCKET_IMAGES/REPORTS/CERTIFICATES`. Los workers `worker-ingestion`, `worker-clustering`, y `worker-analysis` NO los tienen |
| **Impacto** | Workers usan los valores hardcodeados del código (que coinciden, pero no es configurable) |
| **Fix** | Agregar las 3 variables `STORAGE_BUCKET_*` a todos los workers |

---

### ⚠️ PF-7: `worker_prefetch_multiplier` duplicado en `celery_app.py` raíz

| Campo | Detalle |
|-------|---------|
| **Archivo** | `celery_app.py` (root) líneas 50 y 63 |
| **Impacto** | Menor, pero indica código no mantenido/duplicado |

---

## 3. Validación del Flujo de Datos

### 3.1 Workers que Usan GCS (vía `StorageService`)

| Worker Task | Service Intermediario | Bucket Target | Operación |
|-------------|----------------------|---------------|-----------|
| `carousel_task` | `ImageryService` → `StorageService` | `forestguard-images` | Upload thumbnails para carrusel |
| `closure_report_task` | `ClosureReportService` → `StorageService` | `forestguard-images` | Upload imágenes pre/post incendio |
| `exploration_hd_worker` | `StorageService` directamente | `forestguard-images` | Upload imágenes HD de exploración |

### 3.2 Workers que NO Usan GCS (actualmente)

| Worker Task | Service | Almacenamiento |
|-------------|---------|----------------|
| `ingestion` (download_firms_daily) | `load_firms_incremental` | Inserción directa en DB (sin archivos) |
| `clustering` | `DetectionClusteringService` | Solo DB |
| `episode_merge_task` | `EpisodeService` | Solo DB |

### 3.3 Permisos IAM Necesarios (Scopes)

La Service Account de GCS necesita estos roles en cada bucket:

| Role | Bucket | Razón |
|------|--------|-------|
| `roles/storage.objectAdmin` | `forestguard-images` | Upload + delete thumbnails, HD, capas satelitales |
| `roles/storage.objectCreator` | `forestguard-reports` | Upload PDFs de reportes de cierre y evidencia |
| `roles/storage.objectCreator` | `forestguard-certificates` | Upload certificados de auditoría y recibos |

> **Para configurar desde GCP Console:**
> ```bash
> # Otorgar permisos a la Service Account
> SA_EMAIL="gcs-sa@project-fd452487-efa4-4858-8a7.iam.gserviceaccount.com"
> 
> gsutil iam ch serviceAccount:$SA_EMAIL:objectAdmin gs://forestguard-images
> gsutil iam ch serviceAccount:$SA_EMAIL:objectCreator gs://forestguard-reports
> gsutil iam ch serviceAccount:$SA_EMAIL:objectCreator gs://forestguard-certificates
> ```

---

## 4. H3 y GCS (Validación T1.3)

Según la arquitectura, ciertos datos H3 procesados por workers deberían guardarse como archivos **Parquet en GCS** para ahorrar espacio en Supabase.

**Estado actual:**

| Aspecto | Estado | Detalle |
|---------|--------|---------|
| Código de exportación Parquet | ❌ No implementado | No existe worker de exportación |
| `h3_recurrence_stats` | ✅ En PostgreSQL | Vista materializada, no archivos Parquet |
| `fire_events.h3_index` | ✅ En PostgreSQL | Columna `BIGINT` con índice H3 |
| Cálculo de recurrencia | ✅ En BD | Precalculado via vista materializada |

> **Conclusión:** La estrategia Parquet-en-GCS para H3 aún **no está implementada**. Actualmente todos los datos viven en Supabase PostgreSQL. Esto es una optimización post-MVP que requiere un worker dedicado de exportación periódica.

---

## 5. Configuración de Producción Docker Compose (Propuesta)

```yaml
# ── Bloque reutilizable para todos los workers ──
x-worker-env: &worker-env
  # Database
  DB_HOST: ${DB_HOST}
  DB_PORT: ${DB_PORT}
  DB_NAME: ${DB_NAME}
  DB_USER: ${DB_USER}
  DB_PASSWORD: ${DB_PASSWORD}
  # GCS (producción - Service Account JSON montado como secreto Docker)
  GOOGLE_APPLICATION_CREDENTIALS: /run/secrets/gcs-sa-key.json
  GCS_PROJECT_ID: ${GCS_PROJECT_ID}
  STORAGE_BACKEND: gcs
  STORAGE_BUCKET_IMAGES: ${STORAGE_BUCKET_IMAGES:-forestguard-images}
  STORAGE_BUCKET_REPORTS: ${STORAGE_BUCKET_REPORTS:-forestguard-reports}
  STORAGE_BUCKET_CERTIFICATES: ${STORAGE_BUCKET_CERTIFICATES:-forestguard-certificates}
  # Celery
  CELERY_BROKER_URL: redis://redis:6379/0
  CELERY_RESULT_BACKEND: redis://redis:6379/1
  ENVIRONMENT: production

x-worker-config: &worker-config
  build:
    context: .
    dockerfile: Dockerfile.worker
  secrets:
    - gcs-sa-key
  depends_on:
    redis:
      condition: service_healthy
  networks:
    - forestguard
  restart: unless-stopped
  deploy:
    resources:
      limits:
        memory: 512M

secrets:
  gcs-sa-key:
    file: ./secrets/gcs-service-account.json

services:
  worker-ingestion:
    <<: *worker-config
    container_name: forestguard-worker-ingestion
    environment:
      <<: *worker-env
      FIRMS_API_KEY: ${FIRMS_API_KEY}
    command: >
      celery -A workers.celery_app worker
      --loglevel=info --queues=ingestion --concurrency=2

  worker-clustering:
    <<: *worker-config
    container_name: forestguard-worker-clustering
    environment:
      <<: *worker-env
    command: >
      celery -A workers.celery_app worker
      --loglevel=info --queues=clustering --concurrency=2

  worker-analysis:
    <<: *worker-config
    container_name: forestguard-worker-analysis
    environment:
      <<: *worker-env
      GEE_SERVICE_ACCOUNT_JSON: /run/secrets/gcs-sa-key.json
    command: >
      celery -A workers.celery_app worker
      --loglevel=info --queues=analysis --concurrency=1
```

---

## 6. Script de Validación

Se generó `scripts/test_gcs_conn.py` que:

1. Verifica configuración de entorno (env vars, credenciales, ADC)
2. Sube un archivo de 1KB a cada uno de los 3 buckets
3. Reporta el error exacto (403 Forbidden, 404 Not Found, 401 Unauthorized, etc.)
4. Verifica lectura y borrado además de escritura
5. Genera un JSON detallado en `scripts/gcs_diag_report.json`

**Para ejecutar:**
```bash
python scripts/test_gcs_conn.py
```

---

## 7. Resumen de Remediación

| # | Acción | Prioridad | Archivo Afectado |
|---|--------|-----------|------------------|
| 1 | Cambiar `STORAGE_BACKEND=gcs` en `.env` | 🔴 Crítico | `.env:108` |
| 2 | Descomentar/configurar `GOOGLE_APPLICATION_CREDENTIALS` | 🔴 Crítico | `.env:112` |
| 3 | Lazy-init de `gcs_service` global | 🟡 Alto | `app/services/gcs_service.py:395` |
| 4 | Fix user path en docker-compose (`celery` not `user`) | 🟡 Alto | `docker-compose.yml` |
| 5 | Agregar `STORAGE_BUCKET_*` a todos los workers | 🟡 Alto | `docker-compose.yml` |
| 6 | Eliminar o sincronizar `celery_app.py` raíz | 🟢 Medio | `celery_app.py` |
| 7 | Ejecutar `test_gcs_conn.py` para validar | 🟢 Medio | `scripts/test_gcs_conn.py` |
| 8 | Implementar exportación Parquet H3 a GCS | ⚪ Post-MVP | Nuevo worker |

---

*Documento generado: 2026-02-09*  
*Próximos pasos: Ver `gcs_remediation_tasks.md` para el plan de tareas técnicas*
