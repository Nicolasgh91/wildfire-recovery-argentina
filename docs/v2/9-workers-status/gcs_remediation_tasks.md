# 🛠️ Plan de Tareas Técnicas: Remediación GCS Workers

**Referencia:** `gcs_connectivity_diagnostic.md`  
**Fecha:** 2026-02-09  
**Prioridad Global:** Alta — Workers no pueden comunicarse con GCS

---

## Resumen del Plan

| Fase | Tareas | Estimación | Prioridad |
|------|--------|------------|-----------|
| Fase A: Fix Críticos (Local) | 3 tareas | 0.5 días | 🔴 Crítico |
| Fase B: Fix Docker/Producción | 3 tareas | 1 día | 🟡 Alto |
| Fase C: Limpieza de Código | 2 tareas | 0.5 días | 🟢 Medio |
| Fase D: Validación E2E | 2 tareas | 0.5 días | 🟢 Medio |
| Fase E: H3 Parquet Export (Post-MVP) | 4 tareas | 3-4 días | ⚪ Futuro |
| **Total** | **14 tareas** | **~6 días** | |

---

## Fase A: Fix Críticos — Entorno Local

> Estas 3 tareas desbloquean la conectividad GCS para desarrollo local.

### T-GCS-01: Activar STORAGE_BACKEND=gcs en .env
- **Prioridad:** 🔴 Crítico
- **Archivo:** `.env` línea 108
- **Acción:**
  ```diff
  -STORAGE_BACKEND=local #gcs
  +STORAGE_BACKEND=gcs
  ```
- **Riesgo:** Ninguno. El código ya soporta el backend `gcs`.
- **Validación:** Ejecutar `python scripts/test_gcs_conn.py`
- **Estimación:** 5 minutos

---

### T-GCS-02: Configurar credenciales GOOGLE_APPLICATION_CREDENTIALS
- **Prioridad:** 🔴 Crítico
- **Archivo:** `.env` línea 112
- **Opciones de configuración (elegir una):**

  **Opción A — ADC (recomendado para desarrollo):**
  ```bash
  # Ejecutar una sola vez en terminal
  gcloud auth application-default login
  # Esto crea ~/.config/gcloud/application_default_credentials.json
  # El SDK de Google lo detecta automáticamente, no necesita variable de entorno
  ```

  **Opción B — Service Account JSON (recomendado para producción):**
  ```diff
  -#GOOGLE_APPLICATION_CREDENTIALS="C:\ruta\absoluta\service-account-gcs.json"
  +GOOGLE_APPLICATION_CREDENTIALS=./secrets/gcs-service-account.json
  ```
  > **Prerequisito:** Descargar el JSON de la Service Account desde GCP Console → IAM → Service Accounts → Keys

- **Validación:** `python -c "from google.cloud import storage; c = storage.Client(); print('OK')" `
- **Estimación:** 15 minutos

---

### T-GCS-03: Verificar/Crear los 3 buckets en GCS
- **Prioridad:** 🔴 Crítico
- **Acción:** Confirmar que existen en el proyecto `project-fd452487-efa4-4858-8a7`:
  - [ ] `forestguard-images`
  - [ ] `forestguard-reports`
  - [ ] `forestguard-certificates`
- **Comandos de verificación:**
  ```bash
  gsutil ls gs://forestguard-images
  gsutil ls gs://forestguard-reports
  gsutil ls gs://forestguard-certificates
  ```
- **Si no existen, crearlos:**
  ```bash
  gsutil mb -p project-fd452487-efa4-4858-8a7 -l us-central1 gs://forestguard-images
  gsutil mb -p project-fd452487-efa4-4858-8a7 -l us-central1 gs://forestguard-reports
  gsutil mb -p project-fd452487-efa4-4858-8a7 -l us-central1 gs://forestguard-certificates
  ```
- **Permisos IAM necesarios:**
  ```bash
  SA_EMAIL="gcs-sa@project-fd452487-efa4-4858-8a7.iam.gserviceaccount.com"
  gsutil iam ch serviceAccount:$SA_EMAIL:objectAdmin gs://forestguard-images
  gsutil iam ch serviceAccount:$SA_EMAIL:objectCreator gs://forestguard-reports
  gsutil iam ch serviceAccount:$SA_EMAIL:objectCreator gs://forestguard-certificates
  ```
- **Estimación:** 20 minutos

---

## Fase B: Fix Docker / Producción

> Corrige problemas que bloquean el deploy en producción con Docker.

### T-GCS-04: Fix user path mismatch en docker-compose.yml
- **Prioridad:** 🟡 Alto
- **Archivo:** `docker-compose.yml`
- **Problema:** `Dockerfile.worker` crea usuario `celery`, pero docker-compose monta en `/home/user/`
- **Acción:** En los 4 servicios (`api`, `worker-ingestion`, `worker-clustering`, `worker-analysis`):
  ```diff
   environment:
  -  GOOGLE_APPLICATION_CREDENTIALS: /home/user/.config/gcloud/application_default_credentials.json
  +  GOOGLE_APPLICATION_CREDENTIALS: /home/celery/.config/gcloud/application_default_credentials.json
   volumes:
  -  - ~/.config/gcloud:/home/user/.config/gcloud:ro
  +  - ~/.config/gcloud:/home/celery/.config/gcloud:ro
  ```
  > **Nota:** El servicio `api` usa un Dockerfile diferente (`Dockerfile.api`). Verificar qué usuario crea ese Dockerfile. Si también usa `celery`, aplicar el mismo fix. Si usa otro usuario, ajustar acorde.
- **Estimación:** 30 minutos

---

### T-GCS-05: Agregar STORAGE_BUCKET_* a todos los workers
- **Prioridad:** 🟡 Alto
- **Archivo:** `docker-compose.yml`
- **Acción:** Agregar las variables de bucket a `worker-ingestion`, `worker-clustering`, y `worker-analysis`:
  ```yaml
  environment:
    # ... existing vars ...
    STORAGE_BACKEND: gcs
    STORAGE_BUCKET_IMAGES: ${STORAGE_BUCKET_IMAGES:-forestguard-images}
    STORAGE_BUCKET_REPORTS: ${STORAGE_BUCKET_REPORTS:-forestguard-reports}
    STORAGE_BUCKET_CERTIFICATES: ${STORAGE_BUCKET_CERTIFICATES:-forestguard-certificates}
  ```
- **Alternativa superior:** Usar YAML anchors (`x-worker-env`) para evitar duplicación (ver propuesta en `gcs_connectivity_diagnostic.md` sección 5)
- **Estimación:** 20 minutos

---

### T-GCS-06: Configurar Docker Secrets para producción
- **Prioridad:** 🟡 Alto
- **Archivos:** `docker-compose.yml`, `secrets/gcs-service-account.json`
- **Acción:**
  1. Crear directorio `secrets/` (si no existe)
  2. Descargar Service Account JSON de GCP y guardarlo en `secrets/gcs-service-account.json`
  3. Agregar al `docker-compose.yml`:
     ```yaml
     secrets:
       gcs-sa-key:
         file: ./secrets/gcs-service-account.json
     ```
  4. Actualizar cada worker para montar el secreto:
     ```yaml
     services:
       worker-analysis:
         secrets:
           - gcs-sa-key
         environment:
           GOOGLE_APPLICATION_CREDENTIALS: /run/secrets/gcs-sa-key.json
     ```
  5. Verificar que `secrets/` está en `.gitignore`
- **Estimación:** 30 minutos

---

## Fase C: Limpieza de Código

> Elimina deuda técnica y previene crashes futuros.

### T-GCS-07: Lazy-init de GCSService singleton
- **Prioridad:** 🟢 Medio
- **Archivo:** `app/services/gcs_service.py` línea 395
- **Problema:** `gcs_service = GCSService()` se ejecuta al importar el módulo → crashea si falta `GCS_PROJECT_ID`
- **Acción:**
  ```diff
  -# Singleton global
  -gcs_service = GCSService()
  +# Lazy initialization to avoid crashes on import
  +_gcs_service = None
  +
  +def get_gcs_service() -> GCSService:
  +    """Factory function para obtener instancia singleton de GCSService."""
  +    global _gcs_service
  +    if _gcs_service is None:
  +        _gcs_service = GCSService()
  +    return _gcs_service
  ```
- **Impacto secundario:** Buscar en el codebase usos de `from app.services.gcs_service import gcs_service` y migrar a `get_gcs_service()`
- **Estimación:** 30 minutos

---

### T-GCS-08: Consolidar/eliminar celery_app.py duplicado
- **Prioridad:** 🟢 Medio
- **Archivos:** `celery_app.py` (root) y `workers/celery_app.py`
- **Problema:**
  - Root tiene 4 tasks
  - `workers/` tiene 8 tasks (incluye `carousel_task`, `closure_report_task`, `episode_merge_task`, `clustering_task`)
  - Docker usa `workers/celery_app.py` (correcto)
  - `worker_prefetch_multiplier` duplicado en el root
- **Acción recomendada:**
  1. Eliminar `celery_app.py` del root
  2. Si algún script local lo referencia, actualizar a usar `workers.celery_app`
  3. Actualizar documentación que referencie al archivo root
- **Estimación:** 20 minutos

---

## Fase D: Validación End-to-End

### T-GCS-09: Ejecutar test_gcs_conn.py
- **Prioridad:** 🟢 Medio
- **Prerequisitos:** T-GCS-01, T-GCS-02, T-GCS-03 completados
- **Acción:**
  ```bash
  python scripts/test_gcs_conn.py
  ```
- **Resultado esperado:** 3/3 buckets passed (write, read, delete OK)
- **Si falla:** El script reporta el error exacto (403/404/401) con instrucciones de remediación
- **Artefacto:** `scripts/gcs_diag_report.json` con detalle de cada operación
- **Estimación:** 15 minutos

---

### T-GCS-10: Test de worker E2E con GCS
- **Prioridad:** 🟢 Medio
- **Prerequisitos:** T-GCS-09 pasado exitosamente
- **Acción:**
  1. Levantar Redis + workers con Docker:
     ```bash
     docker compose up redis worker-analysis -d
     ```
  2. Disparar una tarea de closure report manualmente:
     ```python
     from workers.celery_app import celery_app
     result = celery_app.send_task(
         'workers.tasks.closure_report_task.generate_closure_reports',
         kwargs={'max_fires': 1}
     )
     print(result.get(timeout=120))
     ```
  3. Verificar en GCS Console que se subió un archivo a `forestguard-images`
- **Estimación:** 30 minutos

---

## Fase E: Exportación Parquet H3 a GCS (Post-MVP)

> **Contexto:** Según la arquitectura documentada, los datos H3 procesados por los workers deberían exportarse como archivos Parquet a GCS para reducir la carga en Supabase PostgreSQL. Actualmente, `h3_recurrence_stats` es una vista materializada en BD. Esta fase implementa el flujo de exportación periódica.

### T-GCS-11: Diseñar esquema de exportación H3
- **Prioridad:** ⚪ Post-MVP
- **Entregable:** Documento de diseño con:
  - Qué tablas/vistas se exportan: `h3_recurrence_stats`, datos de clustering, series temporales H3
  - Formato Parquet: schema de columnas, particionamiento por fecha/región
  - Frecuencia: diaria (post Celery Beat, ej. 04:00 UTC)
  - Naming convention en GCS: `gs://forestguard-images/h3_exports/YYYY/MM/DD/h3_recurrence.parquet`
  - Retención: 90 días de snapshots, luego se archivan a Nearline
- **Dependencias:** T-GCS-01 a T-GCS-10 completados
- **Estimación:** 0.5 días

---

### T-GCS-12: Implementar H3ParquetExportService
- **Prioridad:** ⚪ Post-MVP
- **Archivo nuevo:** `app/services/h3_export_service.py`
- **Responsabilidades:**
  1. Consultar la vista materializada `h3_recurrence_stats` con filtros de fecha
  2. Convertir resultado a DataFrame (pandas/polars)
  3. Exportar a formato Parquet con compresión snappy
  4. Subir a GCS via `StorageService` al bucket `forestguard-images` bajo prefix `h3_exports/`
  5. Registrar metadata de exportación en tabla `data_source_metadata`
- **Librerías requeridas:**
  ```
  pyarrow>=14.0
  pandas>=2.0  # o polars>=0.20 para mejor performance
  ```
- **Esquema Parquet propuesto:**
  ```
  h3_index:           INT64 (H3 cell index)
  total_fires:        INT32
  fires_last_5_years: INT32
  max_frp_ever:       FLOAT32
  total_hectares:     FLOAT64
  recurrence_class:   STRING (enum: high/medium/low)
  recurrence_score:   FLOAT32
  calculated_at:      TIMESTAMP
  export_date:        DATE (partition key)
  ```
- **Pseudocódigo:**
  ```python
  class H3ParquetExportService:
      def __init__(self, db: Session, storage: StorageService):
          self.db = db
          self.storage = storage

      def export_recurrence_stats(self) -> UploadResult:
          # 1. Query h3_recurrence_stats
          rows = self.db.execute(text("SELECT * FROM h3_recurrence_stats")).fetchall()
          
          # 2. Convert to DataFrame
          df = pd.DataFrame(rows, columns=[...])
          
          # 3. Write Parquet to buffer
          buffer = BytesIO()
          df.to_parquet(buffer, engine="pyarrow", compression="snappy")
          
          # 4. Upload to GCS
          today = date.today().isoformat()
          key = f"h3_exports/{today}/h3_recurrence_stats.parquet"
          return self.storage.upload_bytes(
              data=buffer.getvalue(),
              key=key,
              bucket=BUCKETS["images"],
              content_type="application/octet-stream",
              metadata={"export_type": "h3_recurrence", "row_count": str(len(df))}
          )
  ```
- **Estimación:** 1.5 días

---

### T-GCS-13: Crear Celery task para exportación H3
- **Prioridad:** ⚪ Post-MVP
- **Archivo nuevo:** `workers/tasks/h3_export_task.py`
- **Acción:**
  1. Crear task `export_h3_parquet` que invoque `H3ParquetExportService`
  2. Registrar en `workers/celery_app.py`:
     ```python
     include=[
         ...,
         'workers.tasks.h3_export_task',
     ]
     ```
  3. Agregar al beat schedule:
     ```python
     'h3-export-daily': {
         'task': 'workers.tasks.h3_export_task.export_h3_parquet',
         'schedule': crontab(hour=4, minute=0),  # 04:00 UTC (tras clustering)
         'options': {'queue': 'analysis'}
     },
     ```
  4. Agregar routing:
     ```python
     'workers.tasks.h3_export_task.export_h3_parquet': {'queue': 'analysis'},
     ```
- **Estimación:** 0.5 días

---

### T-GCS-14: Lifecycle policy y monitoreo de exports
- **Prioridad:** ⚪ Post-MVP
- **Acciones:**
  1. **Lifecycle policy en GCS** (retención de 90 días + migración a Nearline):
     ```bash
     gsutil lifecycle set lifecycle.json gs://forestguard-images
     ```
     ```json
     {
       "rule": [
         {
           "action": {"type": "SetStorageClass", "storageClass": "NEARLINE"},
           "condition": {"age": 90, "matchesPrefix": ["h3_exports/"]}
         },
         {
           "action": {"type": "Delete"},
           "condition": {"age": 365, "matchesPrefix": ["h3_exports/"]}
         }
       ]
     }
     ```
  2. **Alertas:** Crear alerta en GCP si no hay nuevos archivos en `h3_exports/` por más de 48 horas
  3. **Dashboard metric:** Agregar contador `h3_parquet_exports_total` al sistema de métricas
  4. **Lectura desde frontend:** Endpoint `GET /api/v1/h3/recurrence/download` que genere signed URL al último Parquet
- **Estimación:** 1 día

---

## Diagrama de Dependencias del Plan

```
FASE A (Crítico - 0.5 días)
├── T-GCS-01: STORAGE_BACKEND=gcs
├── T-GCS-02: Configurar credenciales
└── T-GCS-03: Verificar/crear buckets
         │
         ▼
FASE B (Alto - 1 día)                    FASE C (Medio - 0.5 días)
├── T-GCS-04: Fix Docker user path       ├── T-GCS-07: Lazy-init GCSService
├── T-GCS-05: Agregar BUCKET vars        └── T-GCS-08: Consolidar celery_app
└── T-GCS-06: Docker Secrets                      │
         │                                         │
         └─────────────────┬───────────────────────┘
                           ▼
                  FASE D (Medio - 0.5 días)
                  ├── T-GCS-09: test_gcs_conn.py
                  └── T-GCS-10: Test worker E2E
                           │
                           ▼
                  FASE E (Post-MVP - 3-4 días)
                  ├── T-GCS-11: Diseño esquema H3 Parquet
                  ├── T-GCS-12: H3ParquetExportService
                  ├── T-GCS-13: Celery task h3_export
                  └── T-GCS-14: Lifecycle + monitoreo
```

---

*Documento generado: 2026-02-09*  
*Referencia: `gcs_connectivity_diagnostic.md`*  
*Script de validación: `scripts/test_gcs_conn.py`*
