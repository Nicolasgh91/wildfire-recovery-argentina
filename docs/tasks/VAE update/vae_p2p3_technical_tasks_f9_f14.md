# Tareas técnicas: fases F9 a F14 (prioridad P2/P3)

Fecha: 2026-03-12
Prerrequisitos: F1-F8 completados
Referencia: `vae_module_specification.md` secciones 5.3, 8.1, 11, 12

---

## F9: marcadores diferenciados en mapa (P2)

### F9-01: agregar has_active_violation al endpoint de episodios

**Archivo:** endpoint backend que sirve episodios para el mapa (probablemente en `app/api/routes/episodes.py` o equivalente)

Agregar un LEFT JOIN a `land_use_changes` en la query del listado de episodios/eventos para el mapa:

```sql
-- Dentro del SELECT del listado de episodios:
SELECT
    fe.*,
    EXISTS (
        SELECT 1 FROM land_use_changes luc
        WHERE luc.fire_event_id = fe.id
          AND luc.is_potential_violation = true
          AND luc.status = 'pending_review'
    ) AS has_active_violation
FROM fire_events fe
-- ... resto de la query existente
```

Incluir `has_active_violation` en la respuesta JSON.

**Alternativa si la query de episodios es compleja:** agregar el campo como subquery correlacionada solo cuando el usuario está autenticado (para no exponer dato de violaciones a anónimos).

---

### F9-02: inyectar campo en MapPage

**Archivo:** `frontend/src/pages/MapPage.tsx` (~línea 77)

```tsx
// En la función que construye map items:
const mapItem = {
  // ... campos existentes ...
  is_potential_violation: isAuthenticated
    ? (eventOrEpisode.has_active_violation ?? false)
    : false,
};
```

**Archivo:** `frontend/src/types/map.ts` (~línea 18)

Agregar si no existe:
```tsx
is_potential_violation?: boolean;
```

---

### F9-03: verificar que FireMarkers usa el campo

**Archivo:** `frontend/src/components/map/layers/FireMarkers.tsx`

Según AS-IS, las líneas 27 y 93 ya soportan `is_potential_violation` para diferenciación visual. Verificar que el icono/color usado es **discreto** (decisión D-03): no rojo brillante, sino un indicador sutil (borde punteado, icono info pequeño).

Si el soporte actual usa rojo prominente, atenuarlo:
```tsx
// En vez de: fill="#ef4444" (red-500)
// Usar:     fill="#d97706" (amber-600) con opacidad reducida
```

**Verificación:**
```bash
grep -n "is_potential_violation" frontend/src/components/map/layers/FireMarkers.tsx
# Esperado: al menos 1 uso en lógica de icono/color

grep -n "is_potential_violation" frontend/src/pages/MapPage.tsx
# Esperado: al menos 1 asignación
```

---

## F10: dashboard de monitoreo (P2)

### F10-01: crear página /monitoring

**Archivo nuevo:** `frontend/src/pages/MonitoringDashboard.tsx`

Contenido público (sin JWT): totales y distribución de estados desde `GET /monitoring/recovery/summary`.

```tsx
import { useQuery } from "@tanstack/react-query";
import { monitoringEndpoints } from "@/services/endpoints/monitoring";
import { RecoveryStatusBadge } from "@/components/monitoring/RecoveryStatusBadge";
import { LegalDisclaimer } from "@/components/monitoring/LegalDisclaimer";
import { useAuth } from "@/hooks/useAuth";

export default function MonitoringDashboard() {
  const { isAuthenticated } = useAuth();
  const { data: summary, isLoading } = useQuery({
    queryKey: ["recovery-summary"],
    queryFn: () => monitoringEndpoints.getRecoverySummary(),
  });

  if (isLoading) return <DashboardSkeleton />;
  if (!summary) return <p>No hay datos de monitoreo disponibles.</p>;

  return (
    <div className="mx-auto max-w-4xl space-y-6 p-4">
      <h1 className="text-2xl font-semibold">
        Monitoreo de recuperación de vegetación
      </h1>

      {/* Métricas generales — públicas */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
        <SummaryCard
          label="Eventos monitoreados"
          value={summary.total_monitored_events}
        />
        <SummaryCard
          label="Recuperación promedio"
          value={`${summary.average_recovery_percentage?.toFixed(1)}%`}
          sublabel="del baseline"
        />
      </div>

      {/* Distribución por estado — pública */}
      {summary.status_breakdown && (
        <StatusBreakdown breakdown={summary.status_breakdown} />
      )}

      {/* Sección autenticada: lista de eventos con filtros */}
      {isAuthenticated && (
        <AuthenticatedSection />
      )}

      <LegalDisclaimer text={summary.legal_disclaimer} />
    </div>
  );
}
```

La implementación de `StatusBreakdown` puede usar un gráfico de barras horizontales (Recharts `BarChart`) o una tabla simple con badges por estado.

---

### F10-02: agregar ruta en App.tsx

**Archivo:** `frontend/src/App.tsx`

Agregar ruta pública:
```tsx
<Route path="/monitoring" element={<MonitoringDashboard />} />
```

---

### F10-03: agregar endpoint getRecoverySummary al client

**Archivo:** `frontend/src/services/endpoints/monitoring.ts`

```tsx
getRecoverySummary: async () => {
  const response = await api.get("/monitoring/recovery/summary");
  return response.data;
},
```

---

### F10-04: agregar link en navegación

**Archivo:** componente de navegación principal (header/sidebar)

Agregar link a `/monitoring` visible para todos los usuarios:
```tsx
<NavLink to="/monitoring">Monitoreo</NavLink>
```

**Verificación:**
```bash
grep -rn "/monitoring" frontend/src/App.tsx
# Esperado: al menos 1 (Route)

grep -rn "MonitoringDashboard\|monitoring" frontend/src/pages/
# Esperado: archivo existente
```

---

## F11: backfill histórico con dos regímenes (P2)

Fecha de corte: **2025-12-01**. Solo episodios **cerrados** (`extinct`, `closed`).
Episodios activos cubiertos por scheduling regular (beat schedule).

### F11-01: crear tarea de backfill

**Archivo nuevo:** `workers/tasks/backfill.py`

```python
"""
Backfill de datos VAE para episodios cerrados sin monitoreo.
Dos regímenes:
  A) Históricos (start_date < 2025-12-01): puntos semestrales
  B) Recientes (start_date >= 2025-12-01): puntos mensuales
Prioriza episodios en áreas protegidas (relevancia legal ley 26.815).
Cap diario: 5000 req GEE.
One-shot: ejecutar una vez para poblar datos históricos.
"""
import logging
from datetime import date
from dateutil.relativedelta import relativedelta
from sqlalchemy import text

from workers.celery_app import celery_app
from app.db.session import SessionLocal
from workers.tasks.recovery import analyze_recovery

logger = logging.getLogger(__name__)

DAILY_GEE_CAP = 5000
REQUESTS_PER_POINT = 2  # baseline + current
CUTOFF_DATE = date(2025, 12, 1)


def _generate_analysis_points(
    fire_date: date, today: date, interval_months: int
) -> list[date]:
    """Genera lista de fechas de análisis desde fire_date hasta today."""
    points = []
    point = fire_date + relativedelta(months=interval_months)
    while point <= today:
        points.append(point.replace(day=1))
        point += relativedelta(months=interval_months)
    # Agregar punto actual si no coincide con el último
    current_month = today.replace(day=1)
    if not points or points[-1] != current_month:
        points.append(current_month)
    return points


@celery_app.task(queue="vae", soft_time_limit=3600, time_limit=3900)
def backfill_historical_recovery(
    batch_size: int = 50,
    regime: str = "both",  # "A", "B", o "both"
    prioritize_protected: bool = True,
) -> dict:
    """
    Procesa un batch de episodios cerrados sin datos VAE.

    Args:
        batch_size: máximo de episodios a procesar por ejecución.
        regime: "A" (históricos semestral), "B" (recientes mensual),
                "both" (primero A, luego B con el cap restante).
        prioritize_protected: ordenar por áreas protegidas primero.
    """
    db = SessionLocal()
    try:
        today = date.today()
        total_enqueued = 0
        events_processed = 0
        results = {"regime_a": 0, "regime_b": 0}

        # ── Régimen A: históricos cerrados pre-dic 2025, semestral ──
        if regime in ("A", "both"):
            events_a = _fetch_events(
                db, batch_size, before_date=CUTOFF_DATE,
                prioritize_protected=prioritize_protected
            )
            for event in events_a:
                points = _generate_analysis_points(
                    event.start_date, today, interval_months=6
                )
                cost = len(points) * REQUESTS_PER_POINT
                if total_enqueued + cost > DAILY_GEE_CAP:
                    logger.info(f"Cap alcanzado en régimen A: {total_enqueued} req")
                    break
                _enqueue_points(event.id, points)
                total_enqueued += cost
                events_processed += 1
                results["regime_a"] += 1

        # ── Régimen B: recientes cerrados dic 2025+, mensual ──
        if regime in ("B", "both") and total_enqueued < DAILY_GEE_CAP:
            remaining_batch = batch_size - events_processed
            if remaining_batch > 0:
                events_b = _fetch_events(
                    db, remaining_batch, from_date=CUTOFF_DATE,
                    prioritize_protected=prioritize_protected
                )
                for event in events_b:
                    points = _generate_analysis_points(
                        event.start_date, today, interval_months=1
                    )
                    cost = len(points) * REQUESTS_PER_POINT
                    if total_enqueued + cost > DAILY_GEE_CAP:
                        logger.info(f"Cap alcanzado en régimen B: {total_enqueued} req")
                        break
                    _enqueue_points(event.id, points)
                    total_enqueued += cost
                    events_processed += 1
                    results["regime_b"] += 1

        logger.info(
            f"Backfill completado: {events_processed} episodios, "
            f"{total_enqueued} req GEE encolados. "
            f"Régimen A: {results['regime_a']}, B: {results['regime_b']}"
        )
        return {
            "status": "ok",
            "events_processed": events_processed,
            "total_requests_enqueued": total_enqueued,
            **results,
        }

    except Exception as e:
        logger.error(f"Backfill error: {e}", exc_info=True)
        return {"status": "error", "reason": str(e)}
    finally:
        db.close()


def _fetch_events(
    db, batch_size: int,
    before_date: date | None = None,
    from_date: date | None = None,
    prioritize_protected: bool = True,
):
    """Obtiene episodios cerrados sin datos de monitoreo."""
    date_filter = ""
    if before_date:
        date_filter = f"AND fe.start_date < '{before_date.isoformat()}'"
    elif from_date:
        date_filter = f"AND fe.start_date >= '{from_date.isoformat()}'"

    order = """
        ORDER BY
            CASE WHEN fpa.protected_area_id IS NOT NULL THEN 0 ELSE 1 END,
            fe.start_date ASC
    """ if prioritize_protected else "ORDER BY fe.start_date ASC"

    return db.execute(text(f"""
        SELECT DISTINCT fe.id, fe.start_date
        FROM fire_events fe
        LEFT JOIN vegetation_monitoring vm ON vm.fire_event_id = fe.id
        LEFT JOIN fire_protected_area_intersections fpa
            ON fpa.fire_event_id = fe.id
        WHERE vm.id IS NULL
          AND fe.status IN ('extinct', 'closed')
          AND fe.start_date > NOW() - INTERVAL '36 months'
          {date_filter}
        {order}
        LIMIT :batch
    """), {"batch": batch_size}).fetchall()


def _enqueue_points(event_id: str, points: list[date]):
    """Encola analyze_recovery para cada punto de análisis."""
    for point in points:
        analyze_recovery.apply_async(
            args=[str(event_id), point.isoformat()],
            queue="vae",
            priority=9,  # baja prioridad vs scheduling regular
        )
    logger.info(
        f"Backfill: {event_id} → {len(points)} puntos encolados "
        f"({points[0]} a {points[-1]})"
    )
```

**Nota sobre la firma de analyze_recovery:** el worker en F5-03 debe aceptar `target_date_str: str | None = None` como segundo argumento. Verificar consistencia:

```python
# En workers/tasks/recovery.py — firma esperada:
def analyze_recovery(self, fire_event_id: str, target_date_str: str | None = None):
    if target_date_str:
        target_date = date.fromisoformat(target_date_str)
    else:
        target_date = date.today().replace(day=1)
```

---

### F11-02: comandos de ejecución

```bash
# Ejecutar solo régimen A (históricos semestrales):
docker compose exec worker-gee celery -A workers.celery_app call \
  workers.tasks.backfill.backfill_historical_recovery \
  --kwargs='{"batch_size": 100, "regime": "A", "prioritize_protected": true}' -Q vae

# Ejecutar solo régimen B (recientes mensuales):
docker compose exec worker-gee celery -A workers.celery_app call \
  workers.tasks.backfill.backfill_historical_recovery \
  --kwargs='{"batch_size": 50, "regime": "B", "prioritize_protected": true}' -Q vae

# Ejecutar ambos (A primero, B con el cap restante):
docker compose exec worker-gee celery -A workers.celery_app call \
  workers.tasks.backfill.backfill_historical_recovery \
  --kwargs='{"batch_size": 100, "regime": "both"}' -Q vae

# Monitorear progreso por régimen:
psql "$DATABASE_URL" -c "
SELECT
  CASE WHEN fe.start_date < '2025-12-01' THEN 'historico' ELSE 'reciente' END AS regimen,
  COUNT(DISTINCT fe.id) FILTER (WHERE vm.id IS NOT NULL) AS con_monitoreo,
  COUNT(DISTINCT fe.id) FILTER (WHERE vm.id IS NULL) AS sin_monitoreo
FROM fire_events fe
LEFT JOIN vegetation_monitoring vm ON vm.fire_event_id = fe.id
WHERE fe.status IN ('extinct', 'closed')
  AND fe.start_date > NOW() - INTERVAL '36 months'
GROUP BY 1;
"
```

---

## F12: endpoint trigger con rate limit (P3)

Ya especificado en F6-05 (`vae_p1_technical_tasks_f5_f6.md`). No requiere tareas adicionales.

Para completar, el rate limit debe usar la infraestructura existente en `app/core/rate_limiter.py`. Si esa implementación no soporta límites por usuario por ventana temporal (5 req / 6 horas), agregar:

```python
# app/core/rate_limiter.py — extender si es necesario:
import time
from collections import defaultdict

_trigger_limits: dict[str, list[float]] = defaultdict(list)
TRIGGER_MAX = 5
TRIGGER_WINDOW = 6 * 3600  # 6 horas en segundos

def check_trigger_rate_limit(user_id: str):
    """Lanza HTTPException 429 si el usuario excede 5 triggers en 6 horas."""
    now = time.time()
    timestamps = _trigger_limits[user_id]
    # Limpiar expirados
    _trigger_limits[user_id] = [t for t in timestamps if now - t < TRIGGER_WINDOW]
    if len(_trigger_limits[user_id]) >= TRIGGER_MAX:
        raise HTTPException(
            status_code=429,
            detail=f"Límite excedido: máximo {TRIGGER_MAX} disparos cada 6 horas"
        )
    _trigger_limits[user_id].append(now)
```

**Nota:** esta implementación es in-memory y se pierde con restart. Para persistencia, usar Redis (ya disponible como broker Celery).

---

## F13: confidence_score en UI (P3)

### F13-01: poblar confidence_score desde worker

Ya incluido en F5-04. El worker `detect_destruction` persiste `confidence_score` en `land_use_changes`.

### F13-02: mostrar en LandUseChangeCard

Ya incluido en F8-01. La tarjeta muestra `Confianza: X%` en texto secundario.

### F13-03: considerar modelo probabilístico futuro

No requiere implementación ahora. Documentar como deuda técnica:

> La clasificación actual usa heurísticas con umbrales fijos. Un modelo probabilístico que considere: tipo de ecosistema, provincia, estacionalidad, y datos de referencia (IDERA/Copernicus) generaría scores más confiables. Esto requiere un dataset de verdad terrestre que no existe actualmente.

---

## F14: suite de tests (P1 — paralelo a implementación)

### F14-01: tests unitarios para recovery_thresholds

**Archivo nuevo:** `tests/unit/test_recovery_thresholds.py`

```python
import pytest
from app.core.recovery_thresholds import (
    classify_recovery_status,
    RECOVERY_THRESHOLDS,
    ALL_RECOVERY_STATES,
)


class TestClassifyRecoveryStatus:
    """Tests para clasificación unificada de estados."""

    @pytest.mark.parametrize("pct,expected", [
        (95.0, "full_recovery"),
        (90.0, "full_recovery"),
        (89.9, "advanced_recovery"),
        (70.0, "advanced_recovery"),
        (69.9, "moderate_recovery"),
        (40.0, "moderate_recovery"),
        (39.9, "early_recovery"),
        (10.0, "early_recovery"),
        (9.9, "stalled"),
        (0.0, "stalled"),
    ])
    def test_threshold_boundaries(self, pct, expected):
        assert classify_recovery_status(pct) == expected

    def test_none_returns_not_started(self):
        assert classify_recovery_status(None) == "not_started"

    def test_anomaly_overrides_percentage(self):
        assert classify_recovery_status(95.0, has_anomaly=True) == "anomaly_detected"
        assert classify_recovery_status(None, has_anomaly=True) == "anomaly_detected"

    def test_all_states_are_valid(self):
        for state in ALL_RECOVERY_STATES:
            assert isinstance(state, str)
            assert len(state) > 0
```

---

### F14-02: tests unitarios para legal.py

**Archivo nuevo:** `tests/unit/test_legal.py`

```python
from app.core.legal import get_legal_disclaimer, DEFAULT_LEGAL_DISCLAIMER


def test_default_disclaimer():
    assert get_legal_disclaimer() == DEFAULT_LEGAL_DISCLAIMER
    assert "ley 26.815" in get_legal_disclaimer().lower() or "26.815" in get_legal_disclaimer()


def test_override_disclaimer():
    custom = "Texto personalizado de disclaimer."
    assert get_legal_disclaimer(override=custom) == custom


def test_none_override_returns_default():
    assert get_legal_disclaimer(override=None) == DEFAULT_LEGAL_DISCLAIMER
```

---

### F14-03: tests de integración para endpoint recovery

**Archivo nuevo:** `tests/integration/test_monitoring_api.py`

```python
"""
Tests de integración para endpoints de monitoreo.
Requiere BD de test con datos de prueba.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestRecoverySummaryPublic:
    """Summary es público (sin JWT)."""

    def test_returns_200_without_auth(self):
        response = client.get("/api/v1/monitoring/recovery/summary")
        assert response.status_code == 200

    def test_includes_disclaimer(self):
        response = client.get("/api/v1/monitoring/recovery/summary")
        data = response.json()
        assert "legal_disclaimer" in data

    def test_no_violation_data_in_public(self):
        response = client.get("/api/v1/monitoring/recovery/summary")
        data = response.json()
        assert "violation_count" not in data
        assert "changes" not in data


class TestRecoveryDetailAuth:
    """Detalle de recovery con auth diferenciada."""

    def test_returns_200_without_auth(self):
        """Anónimo recibe datos básicos."""
        response = client.get("/api/v1/monitoring/recovery/nonexistent-id")
        # 200 con pending (no 401)
        assert response.status_code in [200, 404]

    def test_returns_annotations_with_auth(self, auth_headers):
        """Autenticado recibe anotaciones de anomalías."""
        response = client.get(
            "/api/v1/monitoring/recovery/test-event-id",
            headers=auth_headers,
        )
        if response.status_code == 200:
            data = response.json()
            if data.get("monitoring_data"):
                first = data["monitoring_data"][0]
                assert "human_activity_detected" in first


class TestLandUseChangesAuth:
    """Cambios de uso requiere JWT."""

    def test_returns_401_without_auth(self):
        response = client.get("/api/v1/monitoring/land-use-changes/any-id")
        assert response.status_code == 401

    def test_returns_200_with_auth(self, auth_headers):
        response = client.get(
            "/api/v1/monitoring/land-use-changes/test-event-id",
            headers=auth_headers,
        )
        assert response.status_code in [200, 404]


class TestTriggerAuth:
    """Trigger requiere admin + rate limit."""

    def test_returns_401_without_auth(self):
        response = client.post(
            "/api/v1/monitoring/recovery/trigger?fire_event_id=test"
        )
        assert response.status_code == 401

    def test_returns_403_non_admin(self, user_headers):
        response = client.post(
            "/api/v1/monitoring/recovery/trigger?fire_event_id=test",
            headers=user_headers,
        )
        assert response.status_code == 403
```

---

### F14-04: tests de idempotencia de workers

**Archivo nuevo:** `tests/integration/test_worker_idempotency.py`

```python
"""
Tests de idempotencia: ejecutar worker 2 veces produce 1 registro.
Requiere BD de test + mock de GEE.
"""
import pytest
from unittest.mock import patch
from sqlalchemy import text
from app.db.session import SessionLocal


@patch("app.services.vae_service.VAEService._get_baseline_ndvi", return_value=0.6)
@patch("app.services.vae_service.VAEService._get_current_ndvi_with_cloud", return_value=(0.45, 15.0))
def test_analyze_recovery_idempotent(mock_current, mock_baseline, test_fire_event_id):
    from workers.tasks.recovery import analyze_recovery

    # Primera ejecución
    result1 = analyze_recovery(test_fire_event_id)
    assert result1["status"] == "ok"

    # Segunda ejecución (mismo mes)
    mock_current.return_value = (0.47, 12.0)
    result2 = analyze_recovery(test_fire_event_id)
    assert result2["status"] == "ok"

    # Verificar: solo 1 registro
    db = SessionLocal()
    try:
        count = db.execute(text("""
            SELECT COUNT(*) FROM vegetation_monitoring
            WHERE fire_event_id = :fid
        """), {"fid": test_fire_event_id}).scalar()
        assert count == 1

        # Verificar que tiene el valor actualizado
        ndvi = db.execute(text("""
            SELECT ndvi_mean FROM vegetation_monitoring
            WHERE fire_event_id = :fid
        """), {"fid": test_fire_event_id}).scalar()
        assert ndvi == pytest.approx(0.47, abs=0.01)
    finally:
        db.close()
```

---

### F14-05: test de queue routing

**Archivo nuevo:** `tests/unit/test_celery_routing.py`

```python
"""Verificar que no quedan referencias a cola 'gee'."""
import pytest


def test_no_gee_queue_in_task_routes():
    from workers.celery_app import celery_app
    routes = celery_app.conf.task_routes or {}
    for task_pattern, config in routes.items():
        queue = config.get("queue", "default")
        assert queue != "gee", (
            f"Task {task_pattern} aún usa cola 'gee'. "
            f"Debe usar 'vae' o 'analysis'."
        )


def test_no_gee_queue_in_beat_schedule():
    from workers.celery_app import celery_app
    schedule = celery_app.conf.beat_schedule or {}
    for name, entry in schedule.items():
        queue = entry.get("options", {}).get("queue", "default")
        assert queue != "gee", (
            f"Beat entry '{name}' usa cola 'gee'. Debe usar 'vae'."
        )


def test_vae_tasks_route_to_vae():
    from workers.celery_app import celery_app
    routes = celery_app.conf.task_routes or {}
    recovery_route = routes.get("workers.tasks.recovery.*", {})
    destruction_route = routes.get("workers.tasks.destruction.*", {})
    assert recovery_route.get("queue") == "vae"
    assert destruction_route.get("queue") == "vae"
```

---

## Verificación integral F9-F14

```bash
# F9: mapa con violaciones
grep -rn "has_active_violation\|is_potential_violation" frontend/src/pages/MapPage.tsx
# Esperado: al menos 1

# F10: dashboard accesible
curl -s http://localhost:3000/monitoring | head -20
# Esperado: HTML de la página de monitoreo

# F11: backfill ejecutable
docker compose exec worker-gee celery -A workers.celery_app call \
  workers.tasks.backfill.backfill_historical_recovery \
  --kwargs='{"batch_size": 5}' -Q vae
# Verificar logs: docker compose logs -f worker-gee --since=2m

# F14: tests pasan
pytest tests/unit/test_recovery_thresholds.py -v
pytest tests/unit/test_legal.py -v
pytest tests/unit/test_celery_routing.py -v
# Esperado: todos green
```

---

## Orden de ejecución consolidado F9-F14

```
F14 (tests)  ←── se puede iniciar en paralelo con cualquier fase
     │
F9 (mapa)   ←── requiere F8 (datos de violaciones)
F10 (dashboard) ←── requiere F6 (summary endpoint)
F11 (backfill) ←── requiere F5 (workers reales)
F12 (trigger) ←── ya especificado en F6-05
F13 (confidence) ←── ya incluido en F5-04 + F8-01
```

---

## Resumen global del roadmap completo

| Fase | Prioridad | Tareas | Esfuerzo estimado | Dependencias |
|---|---|---|---|---|
| **F1: schema** | P0 | 6 | ~1h (migración SQL) | Ninguna |
| **F2: umbrales** | P0 | 4 | ~2h | F1 |
| **F3: colas** | P0 | 5 | ~1h | Ninguna |
| **F4: taxonomía** | P0 | 6 | ~2h | F2 |
| **F5: workers** | P1 | 5 | ~6h | F1, F2, F3 |
| **F6: API** | P1 | 7 | ~4h | F4 |
| **F7: frontend básico** | P1 | 7 | ~4h | F6 |
| **F8: violaciones** | P2 | 4 | ~3h | F5, F6 |
| **F9: mapa** | P2 | 3 | ~2h | F8 |
| **F10: dashboard** | P2 | 4 | ~3h | F6 |
| **F11: backfill** | P2 | 2 | ~2h | F5 |
| **F12: trigger** | P3 | — | Ya en F6-05 | F5 |
| **F13: confidence** | P3 | — | Ya en F5-04 + F8-01 | F8 |
| **F14: tests** | P1 (paralelo) | 5 | ~3h | F2, F3, F5, F6 |
| **Total** | | **58 tareas** | **~33h** | |
