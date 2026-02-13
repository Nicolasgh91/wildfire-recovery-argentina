# Deuda técnica y hallazgos (episode creation flow)

## Convenciones
- Registrar fecha/hora (ISO) por ítem.
- Incluir: contexto, síntomas/logs, causa raíz (si se conoce), impacto, propuesta de solución y prioridad.

## Items
- [2026-02-13T21:20:47Z] Contexto: baseline previo a FG-EP con tests de episodios inestables.
  - Síntomas/logs: `tests/integration/test_fire_episodes_modes.py` fallaba por `307 Temporary Redirect` en `GET /api/v1/fire-episodes` y por asunciones frágiles (UUID vs string y conteo exacto dependiente de datos preexistentes).
  - Causa raíz: ruta declarada solo con trailing slash (`/`) y assertions de test acopladas al estado global del dataset.
  - Impacto: bloqueaba el gate inicial de ejecución secuencial y generaba falsos negativos antes de FG-EP-20.
  - Propuesta de solución: agregar alias de ruta sin slash (`""`) y robustecer asserts del test para validar inclusión/exclusión específica sin depender del total global.
  - Prioridad: alta.
- [2026-02-13T21:30:35Z] Contexto: pruebas de integración FG-EP-20 sobre `fire_detections` en DB local.
  - Síntomas/logs: inserts en `fire_detections` fallaban con `psycopg2.errors.UndefinedFunction: function func_h3(numeric, numeric, integer) does not exist` desde trigger `set_fire_detection_h3_index()`.
  - Causa raíz: trigger legacy depende de `FUNC_H3` no presente en entorno actual.
  - Impacto: cualquier inserción sin `h3_index` explícito rompe pruebas/inserciones de detecciones en este entorno.
  - Propuesta de solución: definir/instalar `FUNC_H3` en entorno dev/test o ajustar trigger para fallback seguro cuando la función no esté disponible.
  - Prioridad: media.
- [2026-02-13T21:37:58Z] Contexto: migración FG-EP-21 (`controlled/extinguished` -> canónico).
  - Síntomas/logs: downgrade completo no puede reconstruir 1:1 qué filas eran `controlled` vs `monitoring` antes de la normalización.
  - Causa raíz: transformación de datos many-to-one (`controlled` y `monitoring` convergen en `monitoring`).
  - Impacto: rollback de datos de estado es funcional pero no perfectamente reversible a nivel histórico.
  - Propuesta de solución: si se requiere reversibilidad total, persistir snapshot previo (tabla audit/backfill log) antes de normalizar.
  - Prioridad: baja.
- [2026-02-13T21:44:12Z] Contexto: lectura de parámetros canónicos FG-EP-22 en servicios.
  - Síntomas/logs: los servicios cachean parámetros canónicos por instancia para reducir consultas repetidas.
  - Causa raíz: optimización local de acceso a `system_parameters` sin invalidación cross-process.
  - Impacto: cambios en `system_parameters` no se reflejan en instancias ya creadas hasta recrear el service/worker.
  - Propuesta de solución: agregar TTL de cache o invalidación explícita basada en `updated_at` si se requiere hot-reload de parámetros.
  - Prioridad: baja.
