## Core Pipeline End‑to‑End — Manual para devs/ops

Este manual explicará cómo:

- Ejecutar el pipeline completo de forma manual (para validaciones puntuales).
- Entender qué tareas Celery/cron cubren cada tramo del pipeline.
- Verificar de punta a punta que:
  - se ingestan detecciones,
  - se crean eventos y episodios,
  - se generan thumbnails/HD,
  - se exponen los datos correctos en la UI.

Se apoyará en:

- `scripts/run_pipeline_manual.py`
- `workers/celery_app.py`
- `docs/flujo-deploy.md`
- `docs/infrastructure/deployment/DEPLOYMENT.md`

