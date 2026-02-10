#### TODO: migrate class Config -> SettingsConfigDict (Pydantic v2)

----
#### Tarea 2.2: Edge Function y RPC para estadísticas públicas (UC-F02)
No, no se desvían.
Lo único “extra” respecto a la lista corta de artefactos de T2.2 fue agregar la vista materializada fire_stats.sql, que sí está explícitamente requerida en el documento maestro (UC‑F02‑001 en 0_master_plan.md) y es necesaria para que el RPC funcione como se validó.

Otros ajustes:

Los casts en get_public_stats.sql solo aseguran que el RPC cumpla su firma (evita el DatatypeMismatch). No cambia la lógica.
El cambio a datetime.now(timezone.utc) es solo en tests para eliminar el warning deprecado.
Si quieres ceñirte estrictamente a la lista de artefactos de T2.2 y no incluir fire_stats.sql, lo puedo revertir, pero el RPC quedaría sin la vista que la propia documentación valida como base.

----
### Validar el egreso de  Supabase: 5GB/mes egreso gratis. 

----
### Tarea 2.3: Servicio de incendios y dashboard (UC-F03)
Acá fallaron los tests


----
### 2026-02-09 - Deuda tecnica detectada al correr pytest
1. `tests/contract/test_schemas.py::test_get_fires_contract` devuelve 307 en `/api/v1/fires` (redireccion por slash).
2. `tests/contract/test_schemas.py::test_certificate_request_contract` falla por respuesta sin `id`, `data_hash`, `created_at`.
3. `tests/e2e/test_audit_flow.py::test_audit_clean_area_e2e` retorna `is_prohibited=True` cuando el test espera `False`.
4. `tests/e2e/test_critical_flows.py::test_contact_flow_e2e` devuelve 422 en `/api/v1/contact`.
5. `tests/e2e/test_fires_uc13.py` falla por 307 en `/api/v1/fires`, 413 en `/api/v1/fires/export` y 422 en `/api/v1/fires/provinces`.
6. `tests/integration/test_fires_db.py` falla por 307 en `/api/v1/fires` y luego JSON invalido.
7. `tests/integration/test_imagery_refresh.py::test_imagery_refresh_admin_success` falla por metodo faltante `ImageryService.refresh_fire`.
8. `tests/unit/test_carousel_task.py::test_carousel_updates_slides_and_images` falla por metodo faltante `ImageryService._fetch_priority_fires`.
9. `tests/unit/test_quality_service.py::test_quality_limitations_missing_assets` falla por funcion DB `func_h3` inexistente en entorno de tests.

----
### Tests pendientes de re-ejecucion (SEC-007)
- `.\.venv\Scripts\pytest.exe --tb=short`
- `.\.venv\Scripts\python.exe -c "from app.main import app; print('Startup OK')"`
