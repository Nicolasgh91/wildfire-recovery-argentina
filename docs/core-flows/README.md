## Flujos CORE y documentación existente

Este directorio agrupa la documentación **canónica** de los flujos CORE de la plataforma y mapea los documentos ya existentes en `docs/` que se relacionan con cada flujo.

- **Tipos de documento**:
  - **overview**: visión general funcional/técnica del flujo.
  - **design**: decisiones de diseño, arquitectura, especificaciones.
  - **manual**: pasos concretos para operar o ejecutar el flujo.
  - **runbook**: troubleshooting e intervención ante incidentes.
  - **histórico**: material útil solo como contexto o snapshot en el tiempo.

### 1. Ingesta de datos satelitales (FIRMS → detecciones/eventos)

- **Documentos existentes relacionados**:
  - `docs/Carrusel fix/data_ingestion_process.md` — **overview/design**
  - `docs/Carrusel fix/flujo_ingesta_procesamiento.md` — **overview** (de extremo a extremo, comparte ámbito con pipeline E2E)
  - `docs/Carrusel fix/auditoria_ingesta_vs_codigo.md` — **design** (auditoría cruzada doc ↔ código)
  - `docs/Carrusel fix/prompt_auditoria_ingesta.md` — **histórico** (contexto de auditoría asistida)
  - `docs/UF-12/0_UC_F12_AS_IS_ANALYSIS_2026-02-24.md` — **histórico/overview** (estado AS-IS previo a la implementación nueva)
  - `docs/UF-12/2_UC_F12_implementation_spec.md` — **design** (especificación de implementación del flujo extendido UC‑F12)
  - `docs/UF-12/3_UC_F12_technical_tasks_claude_code.md` — **histórico/design** (lista técnica de tareas, ya ejecutadas en parte)
  - `docs/UF-12/uc-f12-data-flow-diagram-776569.md` — **overview/design** (diagrama extendido de flujo de datos)
  - `docs/endpoints/fires-stats-workflow.md` — **overview** (flujo de cálculo/lectura de estadísticas de incendios)
  - `docs/endpoints/audit-reverse-geocode-workflow.md` — **overview/design** (enriquecimiento geográfico de detecciones/eventos)
  - `docs/endpoints/error-analysis.md` — **histórico** (análisis de errores anteriores del flujo)

- **Código principal asociado** (referencia rápida):
  - `scripts/maintenance/load_firms_incremental.py`
  - `workers/tasks/ingestion.py`
  - `app/services/detection_clustering_service.py`

### 2. Preprocesamiento de imágenes (thumbnails, watermark, fixes PNG)

- **Documentos existentes relacionados**:
  - `docs/1_home/thumbnails/PNG_CORRUPTION_FIX_SUMMARY.md` — **design** (resumen del fix profundo de PNGs)
  - `docs/1_home/thumbnails/WATERMARK_IMPLEMENTATION_SUMMARY.md` — **design** (diseño de watermark y variantes)
  - `docs/1_home/thumbnails/VM_DEPLOYMENT_COMMANDS.md` — **manual/histórico** (comandos de VM usados durante el fix)
  - `docs/watermark_debugging_guide.md` — **runbook/design** (guía de debugging de corrupción/watermark)
  - `docs/Carrusel fix/revision_arquitectural_flujo_thumbnails.md` — **design** (revisión arquitectural del flujo de thumbnails)
  - `docs/Carrusel fix/thumnails/plan_carrusel_urls_y_hardening.md` — **design** (plan de hardening de URLs y carrusel)
  - `docs/development/runbooks/carousel_manual_run.md` — **runbook/manual** (ejecución manual del carrusel)

- **Código principal asociado**:
  - `app/services/imagery_service.py`
  - `app/utils/watermark.py`
  - `scripts/fix_corrupted_png.py`
  - `scripts/deep_png_fix.py`
  - `scripts/regenerate_fixed_episode.py`
  - `scripts/regenerate_episode_no_watermark.py`
  - `tests/unit/test_thumbnail_pipeline.py`

### 3. Análisis de vegetación VAE / UC‑F12 / NDVI

- **Documentos existentes relacionados**:
  - `docs/UF-12/2_UC_F12_implementation_spec.md` — **design** (especificación de implementación UC‑F12)
  - `docs/UF-12/UC_F12_GEE_optimization_analysis.md` — **design** (optimización sobre GEE para UC‑F12)
  - `docs/UF-12/UC_F12_testing_and_manual_workers.md` — **manual/runbook** (tests y ejecución manual de workers UC‑F12)
  - `docs/UF-12/uc-f12-data-flow-diagram-776569.md` — **overview** (flujo completo de datos UC‑F12)
  - `docs/UF-12/uc-f12-testing-execution-776569.md` — **histórico/manual** (ejecución de pruebas específicas)
  - `docs/ndvi/analisis_ndvi.md` — **overview/design** (análisis NDVI aplicado al dominio)
  - `docs/ndvi/hoja_de_ruta_ndvi_gee_v2.md` — **design** (roadmap técnico NDVI sobre GEE)
  - `docs/ndvi/gee_quota_mitigation_spec_on_ndvi.md` — **design** (mitigación de cuotas GEE para NDVI)
  - `docs/ndvi/pre_deploy_checklist_ndvi_gee.md` — **manual/runbook** (checklist previo a despliegue de NDVI sobre GEE)

- **Código principal asociado**:
  - `app/services/gee_service.py`
  - `app/services/vae_service.py`
  - `workers/tasks/recovery.py`
  - `workers/tasks/destruction.py`
  - `database/migrations/2026_02_23_uc_f12_vae_monitoring.sql`

### 4. Inferencia, recurrencia y exploración HD

- **Documentos existentes relacionados**:
  - `docs/endpoints/fires-stats-workflow.md` — **overview** (flujo de stats de incendios consumidas por UI)
  - `docs/assets-generation/tareas-tecnicas-assets-pipeline.md` — **design/overview** (pipeline técnico de assets: thumbnails, HD, PDFs)
  - `docs/assets-generation/503_implementation_plan.md` — **histórico/design** (plan de implementación, muchas tareas ya ejecutadas)
  - `docs/assets-generation/status_2026-02-22.md` — **histórico** (snapshot de estado a 2026‑02‑22)
  - `docs/development/runbooks/auth-validation.md` — **runbook** (validación de auth que impacta algunos flujos de inferencia protegidos)

- **Código principal asociado**:
  - `app/services/quality_service.py`
  - `app/services/recurrence_service.py`
  - `app/services/exploration_service.py`
  - `app/workers/exploration_hd_worker.py`
  - `app/services/detection_clustering_service.py`

### 5. UI de análisis y mapas

- **Documentos existentes relacionados**:
  - `docs/frontend/README.md` — **overview** (rutas, estado por pantalla, caveats)
  - `docs/frontend/routing_access_ruc.md` — **design/manual** (matriz de acceso por ruta)
  - `docs/frontend/home-removal-incendios-urgentes.md` — **design/histórico** (cambios en home y secciones urgentes)
  - `docs/frontend/ui_debt_log.md` — **histórico/design** (registro de deuda de UI)
  - `docs/architecture/frontend/0_frontend_roadmap.md` — **design** (roadmap alto nivel)
  - `docs/architecture/frontend/1_frontend_technical_tasks.md` — **histórico/design** (tareas técnicas, muchas ya ejecutadas)
  - `docs/architecture/frontend/FE_1.2_desvio.md` — **histórico** (desvíos de versión)

- **Código principal asociado**:
  - `frontend/src/pages/Exploration.tsx`
  - `frontend/src/components/fire-map.tsx`
  - `frontend/src/components/map/MapView.tsx`
  - `frontend/src/components/map/layers/EpisodeLayer.tsx`
  - `frontend/src/components/map/layers/H3HeatmapLayer.tsx`
  - `frontend/src/components/fires/fire-filters.tsx`
  - `frontend/src/components/reliability-score.tsx`

### 6. Pipeline end‑to‑end (detecciones → eventos → episodios → assets → UI)

- **Documentos existentes relacionados**:
  - `docs/INDEX.md` — **overview** (incluye diagrama mermaid del pipeline core)
  - `docs/Carrusel fix/flujo_ingesta_procesamiento.md` — **overview/design** (flujo completo, foco en carrusel)
  - `docs/UF-12/uc-f12-data-flow-diagram-776569.md` — **overview** (flujo extendido con UC‑F12)
  - `docs/assets-generation/tareas-tecnicas-assets-pipeline.md` — **design** (pipeline de assets visuales de punta a punta)
  - `docs/project/episodes/plan_episode_flow.md` — **design/histórico** (diseño del flujo de episodios)
  - `docs/flujo-deploy.md` — **manual/overview** (flujo resumido de deploy y operación)
  - `docs/infrastructure/deployment/DEPLOYMENT.md` — **manual** (guía de despliegue canónica)

- **Código principal asociado**:
  - `scripts/run_pipeline_manual.py`
  - `workers/celery_app.py`
  - `scripts/maintenance/load_firms_incremental.py`

Esta cartografía servirá como base para consolidar la documentación en archivos canónicos dentro de cada subcarpeta `core-*` y para marcar los documentos antiguos como históricos u obsoletos cuando corresponda.

