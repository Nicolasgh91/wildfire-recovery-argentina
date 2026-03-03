## Core VAE / UC‑F12 / NDVI — Overview

Este flujo CORE cubre el análisis de vegetación y recuperación post‑incendio basado en GEE (NDVI/NBR) y el motor VAE.

### Alcance

- Cálculo de índices de vegetación (NDVI/NBR) vía GEE.
- Ejecución periódica de análisis UC‑F12 sobre eventos/episodios.
- Escritura en tablas de monitoreo de vegetación y cambios de uso de suelo.
- Roadmap y límites de cuotas GEE relacionados.

### Código principal

- `app/services/gee_service.py`
- `app/services/vae_service.py`
- `workers/tasks/recovery.py`
- `workers/tasks/destruction.py`
- `database/migrations/2026_02_23_uc_f12_vae_monitoring.sql`

### Documentos fuente relevantes

- `docs/UF-12/2_UC_F12_implementation_spec.md`
- `docs/UF-12/UC_F12_GEE_optimization_analysis.md`
- `docs/UF-12/UC_F12_testing_and_manual_workers.md`
- `docs/UF-12/uc-f12-data-flow-diagram-776569.md`
- `docs/ndvi/analisis_ndvi.md`
- `docs/ndvi/hoja_de_ruta_ndvi_gee_v2.md`
- `docs/ndvi/gee_quota_mitigation_spec_on_ndvi.md`
- `docs/ndvi/pre_deploy_checklist_ndvi_gee.md`

