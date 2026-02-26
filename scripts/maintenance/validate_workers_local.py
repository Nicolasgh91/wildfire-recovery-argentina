#!/usr/bin/env python3
"""
Valida localmente que la configuración de workers (worker-fast + worker-gee)
y las rutas de Celery sean coherentes. No requiere Redis ni DB.
Uso: desde la raíz del repo: python scripts/maintenance/validate_workers_local.py
     o: PYTHONPATH=. python scripts/maintenance/validate_workers_local.py
"""
from __future__ import annotations

import os
import sys

# Asegurar que la raíz del repo esté en PYTHONPATH (como en Docker: /app)
_script_dir = os.path.dirname(os.path.abspath(__file__))
_repo_root = os.path.abspath(os.path.join(_script_dir, "..", ".."))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)


def main() -> int:
    errors: list[str] = []

    # 1. Imports de todos los módulos de tasks (evita SyntaxError/ImportError en runtime)
    print("1. Importando workers.celery_app y módulos de tasks...")
    try:
        from workers.celery_app import celery_app
    except Exception as e:
        errors.append(f"Falló import de workers.celery_app: {e}")
        print(f"   ERROR: {e}")
        for err in errors:
            print(f"   - {err}")
        return 1
    print("   OK: celery_app importado")

    # 2. Rutas: carousel -> analysis (worker-gee), recovery/destruction -> vae (worker-gee)
    print("2. Verificando task_routes...")
    routes = celery_app.conf.task_routes or {}
    expected = {
        "workers.tasks.carousel_task.generate_carousel": "analysis",
        "workers.tasks.recovery.batch_recovery_analysis": "vae",
        "workers.tasks.destruction.batch_destruction_detection": "vae",
        "workers.tasks.ingestion.download_firms_daily": "ingestion",
        "workers.tasks.clustering.cluster_detections": "clustering",
        "workers.tasks.closure_report_task.generate_closure_reports": "reports",
    }
    for task_name, expected_queue in expected.items():
        # Rutas pueden ser por prefijo (workers.tasks.carousel_task.*)
        prefix = task_name.rsplit(".", 1)[0] + ".*"
        route = routes.get(task_name) or routes.get(prefix)
        if not route:
            errors.append(f"Sin ruta para {task_name}")
            continue
        queue = route.get("queue") if isinstance(route, dict) else None
        if queue != expected_queue:
            errors.append(f"{task_name} -> queue {queue}, esperado {expected_queue}")
    if errors:
        for err in errors:
            print(f"   ERROR: {err}")
        return 1
    print("   OK: rutas coherentes con worker-fast (ingestion, clustering, reports) y worker-gee (analysis, vae)")

    # 3. Beat schedule: carousel en cola analysis
    print("3. Verificando beat_schedule (carousel en cola analysis)...")
    beat = celery_app.conf.beat_schedule or {}
    carousel = beat.get("carousel-daily")
    if not carousel:
        errors.append("Falta entrada 'carousel-daily' en beat_schedule")
    elif carousel.get("options", {}).get("queue") != "analysis":
        errors.append(f"carousel-daily debe tener options.queue='analysis', tiene {carousel.get('options')}")
    if errors:
        for err in errors:
            print(f"   ERROR: {err}")
        return 1
    print("   OK: carousel-daily -> queue analysis (worker-gee)")

    # 4. Listar colas que cada worker debe consumir (solo informativo)
    print("4. Resumen de colas por contenedor:")
    print("   worker-fast: ingestion, clustering, reports, notification, default")
    print("   worker-gee:  analysis, vae (incluye generate_carousel)")

    print("\nValidación local OK. Para probar con Docker:")
    print("  docker compose config --quiet && docker compose up -d redis && docker compose up -d worker-gee celery-beat")
    print("  Luego revisar logs: docker compose logs -f worker-gee")
    return 0


if __name__ == "__main__":
    sys.exit(main())
