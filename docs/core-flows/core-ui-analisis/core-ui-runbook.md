## Core UI de Análisis y Mapas — Runbook de troubleshooting

### Escenario 1: Mapa no carga o aparece vacío

**Síntomas**:

- `/map` muestra un canvas en blanco o sin markers/episodios.

**Pasos**:

1. Verificar en consola del navegador si hay errores de JS (por ejemplo, Leaflet, H3, o fetch fallidos).
2. Comprobar que los endpoints usados por el mapa (`/fires`, `/fire-episodes`) responden correctamente (200 con datos).
3. Revisar cambios recientes en tipos `FireMapItem`/`Episode` y en `MapView` para detectar posibles incompatibilidades.

### Escenario 2: Filtros que no devuelven resultados esperados

**Síntomas**:

- Filtrar por provincia/fecha en `/fires/history` devuelve siempre 0 resultados o resultados incorrectos.

**Pasos**:

1. Inspeccionar las llamadas de red del navegador para ver qué query params se envían a `/fires`.
2. Reproducir el filtro manualmente vía curl:

```bash
curl -s "$API_URL/api/v1/fires?province=Corrientes&status_scope=active" | jq '.items | length'
```

3. Si la API devuelve datos pero la UI no, revisar `FireFilters` y el uso de `onFiltersChange`.

### Escenario 3: Problemas de auth/rutas en flujos de análisis

**Síntomas**:

- Usuarios anónimos redirigidos de forma incorrecta.
- Usuarios logueados que no pueden acceder a `/fires/history` o `/exploracion`.

**Pasos**:

1. Revisar `docs/frontend/routing_access_ruc.md` para el comportamiento esperado.
2. Validar en el código de rutas que se está respetando esa matriz (especialmente guards de auth).

### Escenario 4: Datos inconsistentes entre backend y UI

**Síntomas**:

- La UI muestra menos incendios de los que devuelve la API, o viceversa.

**Pasos**:

1. Comparar el payload de `GET /fires`/`/fire-episodes` con lo que se ve en los componentes de lista y mapa.
2. Verificar que el mapeo de tipos (por ejemplo, conversión de lat/lon, estados, severidad) no esté filtrando registros por error.

