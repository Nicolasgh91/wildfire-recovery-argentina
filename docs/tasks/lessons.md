# Lecciones aprendidas — UC-F06 Auditoría de uso de suelo

- **UC-F06 — Estilos de presets y paginación en `/audit`**  
  - Los presets de área y los botones de paginación deben usar siempre la opción A definida en `tasks_UC-06.md`: clases `border-emerald-600 text-emerald-700 hover:bg-emerald-50` sobre `variant="outline"` **solo** cuando el botón no está seleccionado ni deshabilitado.  
  - El preset seleccionado no debe llevar clases emerald de outline; el estado se indica por `variant="default"` y foco visible, no por color verde.  
  - Los tests D-02..D-06 en `frontend/src/pages/__tests__/AuditPage.test.tsx` son obligatorios: cualquier cambio de estilos que los rompa indica un regress y debe revisarse antes de hacer merge.

- **UC-F06 — ID de incendio en resultados de búsqueda (`/audit/search`)**  
  - El campo `fire_event_id` se resuelve en backend (ver `app/api/v1/audit.py`) mediante `LEFT JOIN LATERAL` entre `fire_episodes`, `fire_episode_events` y `fire_events`, usando el criterio `max_frp DESC, start_date ASC` para elegir el evento representativo del episodio.  
  - El esquema `AuditSearchEpisode` en `app/schemas/audit.py` y `frontend/src/types/audit-search.ts` debe exponer siempre `fire_event_id` (string UUID o `null`), nunca omitir la clave.  
  - La columna \"ID de incendio\" en `AuditPage` y la navegación hacia `/fires/:id` dependen de este contrato; cualquier cambio en el SQL debe mantener la misma semántica y ejecutarse junto con los tests de integración `tests/integration/test_audit_search_fire_event_id.py` y los tests de UI D-11..D-14.

