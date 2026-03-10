# Tareas técnicas: hardening del carrusel y estados de episodios

> Documento de tareas técnicas ya ejecutadas o en parte completadas para el hardening del carrusel. El comportamiento vigente está reflejado en `docs/STATE.md`, `docs/architecture/flows.md` y `docs/features/carousel.md`, y la deuda abierta en `docs/tasks/backlog.md`. Conservar este archivo como checklist histórico y guía de referencia.

**Origen:** revisión arquitectónica del 2026-02-24  
**Ejecutor:** Claude Code  
**Rama sugerida:** `fix/carousel-hardening`

---

## Índice de tareas

| Fase | ID | Tarea | Esfuerzo | Dependencias |
|------|----|-------|----------|--------------|
| 0 | CFG-001 | Variables GEE en worker-analysis | 5 min | — |
| 0 | CFG-002 | Comentar variables legacy GCS | 10 min | — |
| 0 | SEC-001 | Autenticación en router monitoring | 5 min | — |
| 0 | SEC-002 | Sanitizar mensajes de error monitoring | 15 min | — |
| 1 | DB-001 | Insertar parámetro episode_temporal_window_hours | 5 min | — |
| 1 | DB-002 | Migración: COALESCE safety en last_seen_at | 10 min | — |
| 2 | CORE-001 | Refactorizar _resolve_episode_status | 30 min | DB-001, DB-002 |
| 2 | CORE-002 | Actualizar defaults canónicos | 10 min | — |
| 2 | CORE-003 | Filtro slides_data en endpoint de episodios | 20 min | — |
| 3 | WORK-001 | Redis lock en carousel worker | 25 min | — |
| 3 | WORK-002 | Retry con backoff por episodio | 25 min | — |
| 3 | WORK-003 | Escritura atómica de slides_data | 20 min | — |
| 3 | WORK-004 | Logging estructurado del carousel | 15 min | — |
| 4 | SEC-003 | Rate limiter en endpoints de generación | 30 min | — |
| 4 | SEC-004 | Hard cap page_size en endpoints de episodios | 10 min | — |
| 5 | SCRIPT-001 | Script de recálculo retroactivo | 25 min | CORE-001 |
| 5 | SCRIPT-002 | Script de verificación E2E | 10 min | Todo lo anterior |
| 6 | DOC-001 | Deprecar fire_events.slides_data | 10 min | — |
| 7 | TEST-001 | Unit tests de estados | 30 min | CORE-001 |
| 7 | TEST-002 | Unit tests de slides_data schema | 15 min | — |
| 7 | TEST-003 | Integration tests de endpoint carrusel | 30 min | CORE-003 |
| 7 | TEST-004 | Worker tests | 30 min | WORK-001..004 |
| 7 | TEST-005 | E2E frontend tests | 20 min | — |

---

## Fase 0: correctivos de configuración y seguridad crítica

*(contenido íntegro del documento original mantenido como histórico, incluyendo CFG-001..SEC-004 y fases posteriores de DB, core, workers, seguridad, scripts y tests; ver archivo completo para el detalle de cada tarea y sus criterios de aceptación.)*

