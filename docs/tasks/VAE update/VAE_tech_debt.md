# Deuda técnica y desvíos — Plan VAE

Registro de desvíos respecto a la especificación y deuda técnica detectada durante la implementación. Cada ítem se revisa y valida antes de documentar.

---

## TD-001: F1 depende de migración previa 2026_02_23

**Fecha:** 2026-03-12  
**Fase:** F1 (schema)  
**Origen:** La migración `2026_02_23_uc_f12_vae_monitoring.sql` ya aplicó en producción F1-01 (UNIQUE), F1-02 (índices), F1-03 (FK + NOT NULL) y RLS (auth + service_role). El plan P0 asumía una única migración nueva.

**Decisión:** No reaplicar lo ya existente. La migración `2026_03_13_vae_schema_hardening.sql` aplica solo F1-04 (columnas nuevas) y F1-05 (política `anon_read_vegetation`). F1 se considera completada si 2026_02_23 está aplicada y 2026_03_13 también.

**Impacto:** Bajo. Quien despliegue en un entorno sin 2026_02_23 debe aplicar primero 2026_02_23 y luego 2026_03_13 (o ejecutar el SQL completo de F1 documentado en P0).

---

## TD-002: Nombre del índice en land_use_changes

**Fecha:** 2026-03-12  
**Fase:** F1 (schema)  
**Origen:** En `vae_p0_technical_tasks.md` (F1-02) el índice se nombra `idx_luc_event`. En `2026_02_23_uc_f12_vae_monitoring.sql` el índice creado es `idx_luc_event_date` sobre las mismas columnas `(fire_event_id, change_detected_at)`.

**Decisión:** Mantener el nombre existente `idx_luc_event_date` en la base. No crear un segundo índice `idx_luc_event`. La especificación de esquema se cumple; solo difiere el nombre del índice.

**Impacto:** Nulo. Código y documentación deben referenciar `idx_luc_event_date` si nombran el índice (p. ej. en rollbacks o scripts de verificación).

---

## TD-003: pending_reason "no_current_image" (worker recovery)

**Fecha:** 2026-03-12  
**Fase:** F5 (workers) — tarea F5-03  
**Origen:** En F5-03 se reescribió el worker `analyze_recovery` para persistir `pending_reason` cuando no hay imagen GEE para el mes actual. La especificación y el documento de tareas P1 usan el valor `no_current_image`; el código anterior devolvía `reason: "no_image_this_month"` sin persistir en BD.

**Decisión:** Usar únicamente `no_current_image` en el worker (retorno del task y valor persistido en `vegetation_monitoring.pending_reason`). No mantener compatibilidad con `no_image_this_month`.

**Impacto:** Bajo. Cualquier cliente que consulte `pending_reason` o el `reason` del resultado del task debe esperar `no_current_image` (o `no_baseline_image`). No se encontraron referencias a `no_image_this_month` en el codebase.
