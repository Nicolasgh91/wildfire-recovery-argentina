## Core VAE / UC‑F12 / NDVI — Runbook de troubleshooting

### Escenario 1: No hay datos en `vegetation_monitoring` ni `land_use_changes`

**Síntomas**:

- UI muestra “análisis pendiente” de forma permanente.
- Consultas a `vegetation_monitoring`/`land_use_changes` dan 0 filas.

**Pasos**:

1. Verificar worker `worker-gee` y colas (ver `UC_F12_testing_and_manual_workers.md`):

```bash
docker ps --format "table {{.Names}}\t{{.Status}}" | grep worker-gee
docker logs forestguard-worker-gee 2>&1 | head -20
```

2. Verificar conteos:

```bash
docker exec forestguard-api python -c "
from app.db.session import SessionLocal
from sqlalchemy import text
db = SessionLocal()
vm = db.execute(text('SELECT count(*) FROM vegetation_monitoring')).scalar()
luc = db.execute(text('SELECT count(*) FROM land_use_changes')).scalar()
print('vegetation_monitoring rows:', vm)
print('land_use_changes rows:', luc)
db.close()
"
```

3. Ejecutar análisis manual para un evento concreto (ver manual dev) y confirmar que aparecen filas nuevas.

### Escenario 2: Workers fallan por errores de GEE o cuota

**Síntomas**:

- Logs de `worker-gee` con excepciones GEE repetidas.
- Tareas `analyze_recovery` o `detect_destruction` reintentando muchas veces.

**Pasos**:

1. Revisar logs recientes:

```bash
docker logs --tail 100 forestguard-worker-gee
```

2. Si los errores indican problemas de cuota (`Computation timed out`, `User memory limit exceeded`):
   - Reducir temporalmente el batch (no lanzar backfill masivo).
   - Ejecutar solo unos pocos eventos para validar funcionalidad.
3. Confirmar que no hay endpoints llamando GEE en tiempo real (según `gee_quota_mitigation_spec_on_ndvi.md`):
   - `GET /monitoring/recovery/*` debe leer solo BD.

### Escenario 3: Inconsistencias entre BD y UI

**Síntomas**:

- La API devuelve datos en `vegetation_monitoring`, pero la UI sigue mostrando “pending” o nada.

**Pasos**:

1. Verificar vía API (con token) que `GET /monitoring/recovery/{fire_event_id}` devuelve `monitoring_data` con filas.
2. Confirmar en frontend:
   - Que el `RecoveryPanel` está condicionado a usuario autenticado.
   - Que se está usando el `fire_event_id` correcto (vista por evento vs episodio).
3. Si el problema está solo en la vista por episodio:
   - Revisar roadmap NDVI (`hoja_de_ruta_ndvi_gee_v2.md`) para el plan de agregación por episodio (puede estar pendiente de implementación).

### Escenario 4: Muchos registros “pending” sin avanzar

**Síntomas**:

- Muchas filas con `recovery_status = 'pending'` o workers devolviendo `{"status": "pending"}`.

**Posibles causas**:

- No hay imágenes pre‑incendio disponibles (baseline no calculable).
- No hay imagen GEE utilizable para el mes actual.

**Pasos**:

1. Revisar logs de `analyze_recovery` buscando `no_baseline_image` o `no_image_this_month`.
2. Validar manualmente en GEE (fuera de este repo) si efectivamente no hay escenas válidas.
3. Aceptar el estado `pending` como final en esos casos y manejarlo en UI como “No hay datos NDVI disponibles para este evento”.

Para detalles de cuotas y arquitectura de workers, ver:

- `docs/UF-12/UC_F12_testing_and_manual_workers.md`
- `docs/ndvi/gee_quota_mitigation_spec_on_ndvi.md`

