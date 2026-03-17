# Plan: Fix API caída por `fire_event_id` duplicado en audit.py

## Contexto

El deploy a prod falla porque **Python 3.11** trata como **SyntaxError** el uso del mismo keyword argument dos veces en una llamada. En [`app/api/v1/audit.py`](app/api/v1/audit.py) la función `_build_episode_items` construye `AuditSearchEpisode` con `fire_event_id` repetido, lo que impide que uvicorn importe el módulo y deja la API caída.

**Ubicación exacta:** líneas 319-336 en `_build_episode_items`.

```316:339:app/api/v1/audit.py
def _build_episode_items(rows: list[dict]) -> list[AuditSearchEpisode]:
    items: list[AuditSearchEpisode] = []
    for row in rows:
        items.append(
            AuditSearchEpisode(
                id=row["id"],
                fire_event_id=row.get("fire_event_id"),   # primera (correcta)
                start_date=row["start_date"],
                ...
                frp_max=float(row["frp_max"])
                if row.get("frp_max") is not None
                else None,
                fire_event_id=row.get("fire_event_id"),   # duplicado — eliminar
            )
        )
    return items
```

---

## Tarea 1: Corregir el argumento duplicado (Error 1)

- **Archivo:** [app/api/v1/audit.py](app/api/v1/audit.py)
- **Cambio:** Eliminar la línea 335 que repite `fire_event_id=row.get("fire_event_id"),`. Dejar una sola asignación de `fire_event_id` (la de la línea 321).
- **Resultado:** El constructor de `AuditSearchEpisode` recibe cada keyword una sola vez; el módulo importa sin SyntaxError y la API puede arrancar.

---

## Tarea 2: Verificación local

- Desde la raíz del repo (donde existe el directorio `app/`):
  ```bash
  python -c "from app.api.v1.audit import router; print('OK')"
  ```
- Si el backend usa un venv o se ejecuta desde otro directorio, ejecutar el mismo comando desde el contexto donde se lanza uvicorn (p. ej. dentro del contenedor o con `PYTHONPATH` apuntando al directorio que contiene `app`).
- Opcional: ejecutar los tests de integración que tocan audit/search y `fire_event_id` (p. ej. `tests/integration/test_audit_search_fire_event_id.py`) para asegurar que el comportamiento de la búsqueda no cambia.

---

## Errores 2 y 3 (sin cambios de código en este plan)

- **Error 2 (worker GEE exit 137):** OOM kill. Acción diferida: una vez la API esté en pie, revisar si el backfill 2016 estaba en curso y si requiere reinicio manual; monitorear RAM del worker (ver [docs/architecture/containers.md](docs/architecture/containers.md) para worker-gee).
- **Error 3 (scans .env):** Informativo; nginx ya bloquea. No requiere acción.

---

## Resumen de criterios de aceptación

| # | Criterio |
|---|----------|
| 1 | Una sola aparición de `fire_event_id=...` en la llamada a `AuditSearchEpisode` dentro de `_build_episode_items`. |
| 2 | `python -c "from app.api.v1.audit import router; print('OK')"` termina con salida `OK`. |
| 3 | Deploy a prod permite que uvicorn arranque y la API responda (p. ej. `/health`). |
