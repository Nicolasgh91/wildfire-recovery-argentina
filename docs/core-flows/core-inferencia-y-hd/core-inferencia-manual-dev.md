## Core Inferencia, Recurrencia y Exploración HD — Manual para devs/ops

### 1. Componentes principales

- **Servicios backend**:
  - `app/services/quality_service.py` (cálculo de reliability score).
  - `app/services/recurrence_service.py` (recurrencia H3).
  - `app/services/exploration_service.py` (gestión de exploraciones HD y assets).
  - `app/workers/exploration_hd_worker.py` (generación de imágenes HD).
- **Frontend**:
  - `frontend/src/pages/Exploration.tsx`.
  - `frontend/src/components/fire-map.tsx` + `MapView`.
  - `frontend/src/components/reliability-score.tsx`.

### 2. Endpoints clave

- Stats e inferencias:
  - `GET /api/v1/fires/stats` — estadísticas agregadas.
  - `GET /api/v1/fires` — listados para map/list.
- Exploración HD:
  - `POST /api/v1/explorations/` — crear exploración.
  - `GET /api/v1/explorations/{id}` — detalle.
  - `POST /api/v1/explorations/{id}/quote` — cotización.
  - `POST /api/v1/explorations/{id}/generate` — disparar generación.
  - `GET /api/v1/explorations/{id}/assets` — listar assets.

### 3. Cómo probar el flujo de recurrencia y stats

1. Asegurarse de que el pipeline base (ingesta + clustering + episodios) corrió recientemente.
2. Consultar stats:

```bash
curl -s "$API_URL/api/v1/fires/stats" | jq
```

3. Comprobar que el mapa (`/map`) muestra el heatmap H3 de recurrencia cuando se activa la capa correspondiente.

### 4. Cómo operar y verificar exploración HD

1. Desde la UI (`/exploracion`):
   - Crear una nueva exploración seleccionando un incendio/episodio.
   - Elegir fechas pre/post y generar cotización.
   - Lanzar generación y esperar a que el estado pase a “completado”.
2. Desde backend (opcional, para debugging):

```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  "$API_URL/api/v1/explorations" | jq '.items[0]'
```

3. Validar que `exploration_hd_worker` está generando activos y subiéndolos a storage consultando `getExplorationAssets` y abriendo manualmente alguna URL de imagen.

### 5. Checks de salud mínimos

- Verificar que `quality_service` esté devolviendo scores razonables para los incendios listados:

```sql
SELECT id, reliability_score
FROM fire_events
ORDER BY start_date DESC
LIMIT 20;
```

- Confirmar que las exploraciones recientes tienen assets asociados:

```sql
SELECT id, status, assets_count
FROM explorations
ORDER BY created_at DESC
LIMIT 20;
```

