# ForestGuard - Casos de Uso v2.0

**Fecha de actualización**: Febrero 2026  
**Total de casos de uso**: 13 (9 implementados, 4 fuera de MVP)  
**Estado**: 85% completado

---

## 1. Visión General

ForestGuard implementa 13 casos de uso diseñados para cubrir el ciclo completo de monitoreo, análisis y fiscalización de incendios forestales en Argentina. Los casos de uso están organizados en 4 categorías:

### 1.1 Categorías de Casos de Uso

```
┌────────────────────────────────────────────────────────────────────────┐
│                    FORESTGUARD USE CASES OVERVIEW                       │
├────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  [1] ACCESO PÚBLICO                                                    │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  UC-F01: Contacto y soporte            [✅ Implementado]         │   │
│  │  UC-F02: Estadísticas públicas         [✅ Implementado]         │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  [2] ANÁLISIS Y CONSULTA (Usuarios Autenticados)                       │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  UC-F03: Histórico y dashboard         [✅ Implementado]         │   │
│  │  UC-F04: Calidad del dato              [✅ Implementado]         │   │
│  │  UC-F05: KPIs de recurrencia           [✅ Implementado]         │   │
│  │  UC-F06: Auditoría legal               [✅ Implementado]         │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  [3] GENERACIÓN DE CONTENIDO (Sistema/Workers)                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  UC-F08: Carrusel satelital            [✅ Implementado]         │   │
│  │  UC-F09: Reporte de cierre             [✅ Implementado]         │   │
│  │  UC-F11: Reportes especializados       [⏳ En progreso]          │   │
│  │  UC-F13: Episodios y metadata GEE      [✅ Implementado]         │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  [4] FUNCIONES PREMIUM (Post-MVP)                                      │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  UC-F07: Registro visitantes offline  [❌ No considerado MVP]   │   │
│  │  UC-F10: Certificación monetizada     [❌ No considerado MVP]   │   │
│  │  UC-F12: Recuperación VAE              [❌ No considerado MVP]   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Casos de Uso Implementados

### UC-F01: Contacto y Soporte

**Estado**: ✅ Implementado  
**Complejidad**: Baja  
**Prioridad**: P2

#### Descripción
Habilita un canal de contacto con adjuntos acotados sin almacenar archivos en base de datos ni storage cloud.

#### Actores
- **Primarios**: Usuarios públicos (no requiere autenticación)
- **Secundarios**: Administradores (reciben emails)

#### Precondiciones
- SMTP configurado (Gmail App Password en producción)
- Rate limiting activo (10 req/min por IP)
- Validaciones de archivo habilitadas

#### Flujo Principal
1. Usuario completa formulario: nombre, email, asunto, descripción
2. (Opcional) Usuario adjunta archivo (tipos permitidos: `.jpg`, `.jpeg`, `.png`, `.pdf`)
3. Frontend valida campos obligatorios client-side
4. Backend valida campos + tipo y tamaño de adjunto
5. Backend encola envío de email (o envía síncrono en MVP)
6. Se registra log técnico mínimo en `audit_events` (sin adjuntos)
7. Se retorna **`202 Accepted`** al frontend

#### Flujos Alternativos

| Escenario | Respuesta | Acción |
|-----------|-----------|--------|
| Archivo > 5 MB | `413 Payload Too Large` | Rechazar con mensaje descriptivo |
| Tipo de archivo no permitido | `422 Unprocessable Entity` | Indicar tipos permitidos |
| Email faltante o inválido | `422 Unprocessable Entity` | Validación Pydantic |
| SMTP caído | `500 Internal Server Error` | Reintentos con backoff exponencial + alerta |

#### Reglas de Negocio

```yaml
Adjuntos:
  tipos_permitidos: [".jpg", ".jpeg", ".png", ".pdf"]
  tamano_maximo: 5 MB
  persistencia: NO (adjunto se envía directo y se descarta)

Rate Limiting:
  limite: 10 requests / minuto por IP
  ventana: sliding window de 60 segundos

Logging:
  nivel: INFO
  datos: email (parcialmente redactado), timestamp, asunto
  NO_registrar: contenido del mensaje, adjuntos
```

#### Datos y Entidades

- **Tablas**: Ninguna (no persiste)
- **Logs**: `audit_events` (opcional, solo metadata)
- **Servicios externos**: Gmail SMTP

#### Endpoints

```http
POST /api/v1/contact
Content-Type: multipart/form-data

Body:
  name: string (required)
  email: string (required, email format)
  subject: string (required)
  message: string (required)
  attachment: file (optional, max 5MB)

Response (202):
{
  "status": "accepted",
  "message": "Tu mensaje ha sido enviado. Te contactaremos pronto."
}
```

#### Criterios de Aceptación

- [x] Respuesta `202` en < 2s para envíos válidos
- [x] Adjuntos inválidos se rechazan con código HTTP correcto
- [x] No se almacenan archivos en BD ni GCS
- [x] Se generan logs para auditoría técnica
- [x] Rate limiting funcional (429 tras superar límite)

#### Restricciones

**FinOps**:
- Costo $0: SMTP gratuito (Gmail App Password)
- Sin costos de storage (no persiste adjuntos)

**Seguridad**:
- Rate limit obligatorio para prevenir spam
- Validación estricta de tipo/tamaño de archivos
- Sanitización de logs (redacción de emails completos)

---

### UC-F02: Estadísticas Públicas Agregadas

**Estado**: ✅ Implementado  
**Complejidad**: Media  
**Prioridad**: P1

#### Descripción
Publica estadísticas agregadas sin exponer tablas directas ni PostgREST. Implementado como Supabase Edge Function que consume RPCs agregadas.

#### Actores
- **Primarios**: Usuarios anónimos (público general)
- **Secundarios**: Edge Function (ejecuta RPC), Cron diario (actualiza vistas)

#### Precondiciones
- RPC `api.public_daily_fire_stats` creada
- RLS configurado: rol `anon` NO tiene acceso directo a tablas
- Cache HTTP activo (s-maxage=3600)
- Rate limiting (100 req/min por IP)

#### Flujo Principal
1. Frontend llama `GET /functions/v1/public-stats?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`
2. Edge Function valida parámetros (rango máximo 730 días)
3. Si rango > 90 días → agregación mensual; si ≤ 90 → agregación diaria
4. Edge Function ejecuta `SELECT * FROM api.public_daily_fire_stats(start_date, end_date)`
5. RPC retorna solo agregados: `frp_max`, `frp_sum`, `total_hectares`, `fires_count`
6. Response con headers de cache: `Cache-Control: public, s-maxage=3600`
7. Cron diario (02:00 UTC) actualiza vista materializada para performance

#### Flujos Alternativos

| Escenario | Respuesta | Acción |
|-----------|-----------|--------|
| Rango > 730 días | `400 Bad Request` | Limitar a 2 años máximo |
| Exceso de requests | `429 Too Many Requests` | Rate limit activo |
| RPC falla | `500 Internal Server Error` | No exponer detalles SQL |
| Rango inválido (end < start) | `400 Bad Request` | Validación de parámetros |

#### Reglas de Negocio

```yaml
Agregación:
  rango_0_90_dias: agregación diaria
  rango_91_730_dias: agregación mensual
  rango_max: 730 días (2 años)

Métricas obligatorias:
  - frp_max: FRP máximo del período
  - frp_sum: Suma total de FRP
  - total_hectares: Hectáreas afectadas
  - fires_count: Total de incendios

Seguridad:
  - Rol anon: SIN acceso directo a fire_events, fire_detections
  - Solo acceso: RPC public_daily_fire_stats
  - Validación: parámetros tipados en RPC
```

#### Datos y Entidades

- **Tablas**: `fire_events`, `fire_detections` (vía RPC, no directo)
- **Vistas**: `fire_stats_daily_mv` (materializada, actualizada diariamente)
- **RPC**: `api.public_daily_fire_stats(start_date DATE, end_date DATE)`

#### Endpoints

```http
GET /functions/v1/public-stats?start_date=2024-01-01&end_date=2024-12-31

Response (200):
{
  "data": [
    {
      "date": "2024-01-01",
      "fires_count": 15,
      "frp_max": 487.3,
      "frp_sum": 2345.7,
      "total_hectares": 1205.4
    },
    ...
  ],
  "aggregation_level": "daily",
  "period": {
    "start": "2024-01-01",
    "end": "2024-12-31",
    "days": 366
  }
}
```

#### Criterios de Aceptación

- [x] Rol `anon` NO puede acceder a tablas/vistas directas
- [x] Respuesta < 2s para rangos comunes (< 90 días)
- [x] Rate limiting efectivo (429 tras 100 req/min)
- [x] Cache operativo (header Cache-Control presente)
- [x] Agregación mensual aplicada cuando corresponde

#### Restricciones

**FinOps**:
- Free tier Supabase Edge Functions (500k invocations/month)
- Cache reduce hits a DB

**Seguridad**:
- **Surface pública mínima**: solo agregados vía Edge/RPC
- RPC con `search_path` fijo: `SET search_path = api, public;`
- Sin wildcards en parámetros de fechas

---

### UC-F03: Histórico de Incendios y Dashboard

**Estado**: ✅ Implementado  
**Complejidad**: Media  
**Prioridad**: P0 (Core)

#### Descripción
Consulta y análisis de históricos con dashboard y grilla filtrable para usuarios autenticados. Incluye exportación CSV/JSON.

#### Actores
- **Primarios**: Usuarios autenticados (analistas, periodistas, ONGs)
- **Secundarios**: API FastAPI (valida filtros), Servicios de exportación

#### Precondiciones
- Usuario autenticado (JWT válido)
- Tabla `fire_events` con datos
- Índices activos en `start_date`, `province`, `status`
- Vista `fire_stats` disponible

#### Flujo Principal
1. Usuario abre `/fires` en frontend
2. Usuario define filtros: fecha, provincia, estado, búsqueda texto
3. Frontend llama:
   - `GET /api/v1/fires?page=1&page_size=20&filters={...}` (grilla)
   - `GET /api/v1/fires/stats?filters={...}` (KPIs de dashboard)
4. API retorna grilla paginada + KPIs sincronizados
5. Usuario visualiza tabla responsiva (mobile: cards, desktop: tabla)
6. (Opcional) Usuario exporta resultados: `GET /api/v1/fires/export?format=csv&filters={...}`
7. Se genera CSV/JSON con los mismos filtros aplicados

#### Flujos Alternativos

| Escenario | Respuesta | Acción |
|-----------|-----------|--------|
| Filtros inválidos | `400 Bad Request` | Validación Pydantic |
| Sin resultados | `200 OK` con `[]` | Lista vacía, no error |
| Export muy grande (> 10k registros) | `413 Payload Too Large` | Limitar o usar paginación |
| Usuario no autenticado | `401 Unauthorized` | Redirect a `/login` |

#### Reglas de Negocio

```yaml
Paginación:
  page_size_default: 20
  page_size_max: 100 (hard cap)
  mobile_max: 50

Filtros disponibles:
  - start_date: rango de fechas
  - province: lista de provincias (multi-select)
  - status: [active, extinguished, contained]
  - search: texto libre (ILIKE en name, province)

Exportación:
  formatos: [csv, json]
  max_records: 10,000
  respeta_filtros: true
```

#### Datos y Entidades

- **Tablas**: `fire_events`, `fire_detections`, `fire_protected_area_intersections`
- **Vistas**: `fire_stats` (agregados por provincia)
- **Schemas**: `FireEventResponse`, `FireStatsResponse`

#### Endpoints

```http
# Grilla paginada
GET /api/v1/fires?page=1&page_size=20&province=Córdoba&status=active

Response (200):
{
  "items": [{
    "id": "uuid",
    "name": "Incendio Punilla",
    "province": "Córdoba",
    "start_date": "2024-02-01",
    "status": "extinguished",
    "estimated_area_hectares": 1250.5,
    "max_frp": 487.3
  }, ...],
  "total": 150,
  "page": 1,
  "page_size": 20,
  "total_pages": 8
}

# KPIs de dashboard
GET /api/v1/fires/stats?province=Córdoba

Response (200):
{
  "total_fires": 150,
  "total_hectares": 45000.2,
  "avg_duration_days": 4.2,
  "by_status": {
    "active": 5,
    "extinguished": 140,
    "contained": 5
  }
}

# Exportación
GET /api/v1/fires/export?format=csv&province=Córdoba&max_records=1000

Response (200):
Content-Type: text/csv
Content-Disposition: attachment; filename="fires_export_2024-02-09.csv"

id,name,province,start_date,status,area_hectares
...
```

#### Criterios de Aceptación

- [x] Dashboard carga < 1s con filtros comunes
- [x] Filtros aplican igual en grilla, KPIs y export
- [x] Solo usuarios autenticados pueden acceder
- [x] Paginación server-side funcional
- [x] Export respeta filtros activos

#### Restricciones

**FinOps**:
- Límite Supabase 500 MB → particionado/archivado de `fire_detections` tras 90 días
- Evitar queries sin índices (monitored con `pg_stat_statements`)

**Performance**:
- Índices compuestos: `(start_date DESC, province)`
- Vista `fire_stats` actualizada cada 24h

---

### UC-F04: Calidad y Confiabilidad del Dato

**Estado**: ✅ Implementado  
**Complejidad**: Media  
**Prioridad**: P1

#### Descripción
Expone un score de confiabilidad reproducible por evento con metadata de fuentes y limitaciones.

#### Actores
- **Primarios**: Peritos judiciales, investigadores, periodistas de datos
- **Secundarios**: Quality Service (calcula score)

#### Precondiciones
- Tabla `data_source_metadata` poblada
- Vista `fire_event_quality_metrics` disponible
- Usuario autenticado (o público si se decide exponer métricas básicas)

#### Flujo Principal
1. Usuario solicita quality metrics de un incendio: `GET /api/v1/quality/{fire_event_id}`
2. API consulta vista `fire_event_quality_metrics` (precomputada)
3. Se obtiene `reliability_score` (0-100) y clasificación (`high`, `medium`, `low`)
4. Se adjuntan fuentes utilizadas (NASA FIRMS, Sentinel-2, Open-Meteo)
5. Se incluyen limitaciones conocidas (ej: "Sin datos climáticos para este período")
6. Response con score + metadata + limitaciones

#### Flujos Alternativos

| Escenario | Respuesta | Acción |
|-----------|-----------|--------|
| Evento inexistente | `404 Not Found` | Fire event ID inválido |
| Metadata incompleta | `200 OK` con warnings | Score degradado + disclaimers |

#### Reglas de Negocio

```yaml
Ponderación del Score:
  confianza_detecciones: 40%
  imagenes_satelitales: 20%
  datos_climaticos: 20%
  detecciones_independientes: 20%

Clasificación:
  high: score >= 80
  medium: score 50-79
  low: score < 50

Transparencia:
  - Fuentes siempre visibles
  - Limitaciones explícitas
  - Fórmula de score documentada
```

#### Datos y Entidades

- **Tablas**: `data_source_metadata`, `fire_events`, `satellite_images`, `climate_data`
- **Vistas**: `fire_event_quality_metrics` (precomputada)
- **Schema**: `QualityMetricsResponse`

#### Endpoints

```http
GET /api/v1/quality/fire-event/{fire_event_id}

Response (200):
{
  "fire_event_id": "uuid",
  "reliability_score": 85.5,
  "classification": "high",
  "score_breakdown": {
    "detection_confidence": 40,
    "satellite_imagery": 18,
    "climate_data": 20,
    "independent_detections": 7.5
  },
  "sources": [
    {
      "name": "NASA FIRMS VIIRS",
      "confidence_level": "high",
      "resolution_m": 375
    },
    {
      "name": "Sentinel-2",
      "resolution_m": 10,
      "cloud_coverage_pct": 5.2
    }
  ],
  "limitations": [
    "No hay datos climáticos disponibles para este período",
    "Cobertura de nubes > 10% en algunas imágenes"
  ],
  "calculated_at": "2024-02-09T14:30:00Z"
}
```

#### Criterios de Aceptación

- [x] Score reproducible y documentado
- [x] Incluye metadata de fuentes
- [x] Limitaciones explícitas en response
- [x] Respuesta < 1s (vista precomputada)
- [x] Fórmula versionada (v1.0 documentada)

#### Restricciones

**FinOps**:
- Vista materializada actualizada diariamente (no en tiempo real)
- No exponer métricas sensibles a usuarios no autenticados

**Calidad**:
- Fórmula de score versionada en código y documentación
- Metadata de fuentes obligatoria para todos los incendios

---

### UC-F05: KPIs de Recurrencia y Tendencias

**Estado**: ✅ Implementado  
**Complejidad**: Media  
**Prioridad**: P1

#### Descripción
Identifica patrones de recurrencia y tendencias espaciales/temporales para dashboards analíticos usando índice H3.

#### Actores
- **Primarios**: ONGs, fiscalías, analistas ambientales
- **Secundarios**: H3 Analysis Service

#### Precondiciones
- Columna `h3_index` poblada en `fire_events`
- Vista materializada `h3_recurrence_stats` actualizada
- Índice GIST en geometrías

#### Flujo Principal
1. Usuario define área (bbox) y rango temporal en dashboard
2. Frontend llama `GET /api/v1/analysis/recurrence?bbox=-65,-32,-63,-30&start_date=2019-01-01`
3. API consulta vista `h3_recurrence_stats` para celdas H3 en bbox
4. Se calculan densidades, clasificaciones de recurrencia (`low`, `medium`, `high`)
5. (Opcional) Se ejecuta regresión lineal básica para tendencias temporales
6. Response con GeoJSON para visualización en mapa

#### Flujos Alternativos

| Escenario | Respuesta | Acción |
|-----------|-----------|--------|
| BBOX demasiado grande (> 10°) | `400 Bad Request` | Limitar área de consulta |
| Sin datos en área | `200 OK` con `features: []` | GeoJSON vacío |
| Rango temporal > 10 años | `200 OK` con agregación mensual | Reducir granularidad |

#### Reglas de Negocio

```yaml
Clasificación de Recurrencia (últimos 5 años):
  low: < 1 incendio / 5 años
  medium: 1-3 incendios / 5 años
  high: > 3 incendios / 5 años

H3 Spatial Indexing:
  resolution: 7 (hexágonos de ~5 km²)
  agregacion: COUNT(*) por h3_index

Tendencias:
  método: regresión lineal simple (incendios/año)
  intervalos: confidence intervals del 95%
```

#### Datos y Entidades

- **Tablas**: `fire_events` (con `h3_index`)
- **Vistas**: `h3_recurrence_stats` (materializada)
- **Schema**: `RecurrenceAnalysisResponse`

#### Endpoints

```http
GET /api/v1/analysis/recurrence?bbox=-65,-32,-63,-30&start_date=2019-01-01&end_date=2024-02-09

Response (200):
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[...]]]  # H3 cell boundary
      },
      "properties": {
        "h3_index": "87283472fffffff",
        "total_fires": 12,
        "fires_last_5_years": 5,
        "recurrence_class": "high",
        "max_frp": 587.3,
        "total_hectares": 2450.7
      }
    },
    ...
  ],
  "summary": {
    "total_cells": 45,
    "high_recurrence_cells": 8,
    "medium_recurrence_cells": 20,
    "low_recurrence_cells": 17
  }
}

GET /api/v1/analysis/trends?province=Córdoba&start_year=2015

Response (200):
{
  "province": "Córdoba",
  "period": {"start": 2015, "end": 2024},
  "annual_fires": [
    {"year": 2015, "count": 45},
    {"year": 2016, "count": 52},
    ...
  ],
  "trend_analysis": {
    "slope": 2.3,  # +2.3 incendios/año
    "direction": "increasing",
    "confidence_interval": [1.8, 2.8],
    "r_squared": 0.78
  }
}
```

#### Criterios de Aceptación

- [x] KPIs consistentes con filtros de dashboard
- [x] Respuesta < 2s para rangos comunes (< 90 días, bbox moderado)
- [x] Exportable en GeoJSON/CSV
- [x] Vista H3 actualizada diariamente

---

### UC-F06: Verificación de Terreno (Auditoría Legal)

**Estado**: ✅ Implementado  
**Complejidad**: Alta  
**Prioridad**: P0 (Core Legal)

#### Descripción
Permite a usuarios no técnicos investigar el historial de incendios en un terreno mediante búsqueda por ubicación (dirección, localidad, parque nacional), mapa interactivo y validación legal según Ley 26.815. La interfaz guía la exploración con enfoque de curiosidad e investigación ciudadana, determinando prohibiciones legales de uso del suelo basándose en incendios históricos dentro de un área especificada.

#### Actores
- **Primarios**: Público general (ciudadanos, periodistas, investigadores amateurs), Escribanos, inspectores de bancos, compradores de propiedades
- **Secundarios**: Audit Service, GEE Service (para evidencia visual)

#### Precondiciones
- Tabla `protected_areas` cargada y actualizada
- Vista `fire_protected_area_intersections` disponible
- API key válida (autenticación obligatoria)
- Hard cap de radio configurado en `system_parameters`

#### Flujo Principal

**UX Flow (Frontend):**
1. Usuario busca lugar por dirección, localidad, parque nacional o provincia (o marca punto en mapa interactivo)
2. Usuario selecciona **área de análisis** usando opciones predefinidas:
   - **Alrededores (500 m)**
   - **Zona (1 km)**
   - **Amplio (3 km)**
   - Personalizado (en Opciones Avanzadas)
3. (Opcional) Usuario expande "Opciones Avanzadas" para ajustar coordenadas exactas, ID catastral o radio personalizado
4. Usuario presiona **"Verificá"** (CTA principal)
5. Se muestra **checklist de verificación** y estados informativos (cargando → resultados)

**Backend Flow:**
1. Frontend envía POST `/api/v1/audit/land-use` con `lat`, `lon`, `radius_meters` (convertidos del selector de área)
2. API valida radio (max 5000m según hard cap)
3. Se buscan `fire_events` dentro del radio usando PostGIS `ST_DWithin`
4. Se cruzan eventos con `protected_areas` para determinar categoría de protección
5. Se calcula `prohibition_until`:
   - **60 años** si afecta bosques nativos/áreas protegidas
   - **30 años** en zonas agrícolas/praderas
6. Se adjunta evidencia visual (thumbnail satelital si existe metadata GEE)
7. Se registra auditoría en tabla `land_use_audits` (append-only, inmutable)
8. Response con `is_violation`, `prohibition_until`, lista de incendios encontrados

#### Flujos Alternativos

| Escenario | Respuesta | Acción |
|-----------|-----------|--------|
| Sin incendios en radio | `200 OK` con `is_violation: false` | Respuesta negativa válida |
| Falta protected_areas en zona | `200 OK` con warning | Respuesta parcial + disclaimer |
| Imagen no disponible | `200 OK` sin evidencia visual | Solo metadata del incendio |
| Radio > 5000m | `422 Unprocessable Entity` | Hard cap configurado |

#### Reglas de Negocio

```yaml
Ley 26.815 (Argentina):
  bosques_nativos: 60 años de prohibición
  areas_protegidas: 60 años
  zonas_agricolas: 30 años
  praderas: 30 años

Configuración:
  radius_default_m: 500
  radius_max_m: 5000 (hard cap en system_parameters)
  requiere_autenticacion: true
  rate_limit: 20 req/hora

UX:
  area_analysis_presets: ["Alrededores (500 m)", "Zona (1 km)", "Amplio (3 km)"]
  search_by: ["dirección", "localidad", "parque nacional", "provincia"]
  cta_principal: "Verificá"
  checklist_items:
    - "¿Hubo incendios en los últimos años en esta zona?"
    - "¿La vegetación se recuperó o quedó degradada?"
    - "¿Persisten señales del incendio en el área?"
    - "¿Qué dicen fuentes públicas y registros locales?"
  microcopy:
    - "Algunos incendios son accidentales; otros pueden tener intereses detrás. Acá podés mirar evidencia y sacar tus conclusiones."
    - "Esto no demuestra intencionalidad por sí solo. Sirve para contrastar relatos con evidencia observable."

Audit Logging:
  tabla: land_use_audits (append-only)
  inmutable: true (no DELETE ni UPDATE permitidos)
  retencion: indefinida (compliance legal)
```

#### Datos y Entidades

- **Tablas**: `fire_events`, `protected_areas`, `fire_protected_area_intersections`, `land_use_audits`, `satellite_images`
- **Schemas**: `LandUseAuditRequest`, `LandUseAuditResponse`

#### Endpoints

```http
POST /api/v1/audit/land-use
Content-Type: application/json
Authorization: Bearer <jwt_token>
X-API-Key: <api_key>

Body:
{
  "latitude": -31.42,
  "longitude": -64.18,
  "search_radius_meters": 1000  # Convertido de selector "Zona (1 km)"
}

# Nota: Frontend presenta búsqueda por lugar, mapa interactivo y selector de área.
# Backend continúa recibiendo lat/lon/radius_meters.

Response (200):
{
  "is_violation": true,
  "prohibition_until": "2084-03-15",  # 60 años desde último incendio
  "fires_found": 3,
  "fires": [
    {
      "id": "uuid",
      "name": "Incendio Sierras Chicas",
      "start_date": "2024-03-15",
      "distance_meters": 450.2,
      "protected_area": {
        "name": "Parque Nacional Quebrada del Condorito",
        "category": "bosque_nativo"
      },
      "evidence": {
        "thumbnail_url": "https://storage.googleapis.com/.../thumbnail.webp",
        "gee_system_index": "20240315T141234_20240315T141234_T20JLK"
      }
    },
    ...
  ],
  "audit_id": "uuid",
  "audit_hash": "sha256:abc123...",
  "requested_at": "2024-02-09T18:30:00Z"
}
```

#### Criterios de Aceptación

- [x] Respuesta < 2s para consultas normales
- [x] Fechas de prohibición calculadas correctamente según Ley 26.815
- [x] Evidencia visual incluida cuando existe metadata GEE
- [x] Audit log inmutable registrado
- [x] Hash SHA-256 verificable para validez legal

#### Restricciones

**FinOps**:
- Intersecciones precalculadas (no on-demand)
- Thumbnails desde GCS (no generar en tiempo real)

**Seguridad**:
- API key obligatoria + JWT
- Rate limit estricto (20 req/hora)
- No exponer tablas a clientes directamente

**Legal**:
- Audit log append-only (no DELETE/UPDATE)
- Hash verificable para trazabilidad

---

### UC-F08: Carrusel Satelital de Incendios Activos

**Estado**: ✅ Implementado  
**Complejidad**: Alta  
**Prioridad**: P1

#### Descripción
Genera slides diarios de imágenes satelitales para incendios activos sin consultar GEE en tiempo real. Worker diario con validación de nubosidad adaptativa. **Alimenta la experiencia de Exploración Satelital** en frontend con thumbnails progresivos que permiten comparación temporal (antes/durante/después).

#### Actores
- **Primarios**: Sistema (Celery Beat + Worker)
- **Secundarios**: GEE Service, GCS Storage

#### Precondiciones
- Tabla `fire_events` con eventos `status = 'active'`
- Acceso a GEE configurado (`GOOGLE_APPLICATION_CREDENTIALS`)
- Bucket GCS `images` disponible
- Parámetro `MAX_CLOUD_COVERAGE` en `system_parameters`

#### Flujo Principal
1. **Trigger**: Celery Beat ejecuta task diaria (01:00 UTC)
2. Listar `fire_events` con `status = 'active'` y priorizar por:
   - 40% proximidad a áreas protegidas
   - 30% FRP (Fire Radiative Power)
   - 20% área quemada
   - 10% recurrencia H3
3. Para cada evento (batch de 15 max):
   - Buscar mejor imagen Sentinel-2 en ventana de 7 días con menor nubosidad
   - Validar `cloud_coverage < MAX_CLOUD_COVERAGE` (adaptativo: 10% → 20% → 30%)
4. Si `gee_system_index` es nuevo:
   - Generar 3 thumbnails (SWIR, RGB, NBR) de 512x512px en WebP
   - Subir a `gs://images/fires/{fire_id}/thumbnails/`
   - Actualizar `satellite_images` con metadata GEE
   - Registrar `last_gee_image_id` y `last_update_sat` en `fire_events`
5. Si `gee_system_index` coincide → Skip (ya existe)

#### Flujos Alternativos

| Escenario | Respuesta | Acción |
|-----------|-----------|--------|
| Nubosidad alta (> 30%) | Omitir evento | Reintentar en siguiente corrida |
| Sin incendios activos | Task completa sin error | Log INFO |
| Cuota GEE excedida | Abortar batch | Reprogramar task 6h después + alerta |
| GCS upload falla | Reintentar 3 veces | Dead Letter Queue si persiste |

#### Reglas de Negocio

```yaml
Priorización (ponderada):
  proximidad_area_protegida: 40%
  frp_max: 30%
  area_hectares: 20%
  recurrencia_h3: 10%

Cloud Coverage Adaptativo:
  threshold_inicial: 10%
  threshold_fallback_1: 20%
  threshold_fallback_2: 30%
  max_threshold: 50% (si > 50%, se omite)

Batch Processing:
  max_fires_per_run: 15
  ventana_temporal: 7 días
  formato_imagen: WebP (compresión 80%)
  resolucion_thumbnail: 512x512px

Idempotencia:
  - No regenera si gee_system_index coincide
  - Check antes de cada generación
```

#### Datos y Entidades

- **Tablas**: `fire_events`, `satellite_images`, `system_parameters`
- **Storage**: GCS `gs://images/fires/{fire_id}/thumbnails/`
- **Worker**: `workers.tasks.imagery.generate_carousel`

#### Celery Task

```python
# workers/tasks/imagery.py
@app.task(bind=True, base=DLQTask, max_retries=3)
def generate_carousel(self):
    """Daily task to generate satellite image carousel for active fires."""
    fires = get_active_fires_prioritized(limit=15)
    
    for fire in fires:
        try:
            best_image = gee_service.find_best_image(
                fire.centroid,
                days_back=7,
                max_cloud=get_adaptive_cloud_threshold(fire)
            )
            
            if best_image.system_index == fire.last_gee_image_id:
                logger.info(f"Image already exists for {fire.id}, skipping")
                continue
            
            thumbnails = gee_service.generate_thumbnails(
                best_image,
                bands=['SWIR', 'RGB', 'NBR'],
                size=512
            )
            
            storage_service.upload_thumbnails(fire.id, thumbnails)
            
            fire.update(
                last_gee_image_id=best_image.system_index,
                last_update_sat=datetime.utcnow()
            )
            
        except GEEQuotaExceeded:
            raise self.retry(countdown=6 * 3600)  # 6 hours
```

#### Criterios de Aceptación

- [x] Actualiza solo cuando hay imagen nueva (idempotente)
- [x] Completa batch de 15 incendios en < 5 min
- [x] No usa GEE en tiempo real para UI (solo worker diario)
- [x] Priorización ponderada funcional
- [x] Cloud coverage adaptativo (10% → 20% → 30%)

---

### UC-F09: Reporte de Cierre Pre/Post Incendio

**Estado**: ✅ Implementado  
**Complejidad**: Alta  
**Prioridad**: P1

#### Descripción
Genera evidencia visual de cierre con imágenes pre/post incendio cuando el evento finaliza, con cálculo de dNBR (difference Normalized Burn Ratio). **Provee datos para la experiencia de Exploración Satelital** con comparación temporal y análisis de severidad del impacto.

#### Actores
- **Primarios**: Sistema (Celery Worker)
- **Secundarios**: Analistas ambientales (consumen reportes)

#### Precondiciones
- `fire_events` con `status = 'extinguished'` o `'contained'`
- `extinguished_at` NOT NULL
- GEE operativo
- Bucket GCS disponible

#### Flujo Principal
1. **Trigger**: Celery Beat ejecuta task diaria (02:00 UTC) o evento de cambio de status
2. Buscar eventos extinguidos en últimas 24h con `has_closure_report = false`
3. Para cada evento:
   - **Imagen PRE**: Buscar -15 a -7 días desde `start_date` (fallback -30 días)
   - **Imagen POST**: Buscar desde `extinguished_at` + 7 días (esperar revegetación inicial)
4. Validar nubosidad < 40% (con cloud masking si aplica)
5. Generar 3 slides comparativos:
   - Before/After RGB
   - Before/After NDVI
   - dNBR (Normalized Burn Ratio difference)
6. Calcular `dnbr_mean` y clasificación de severidad:
   - < 0.1: Low severity
   - 0.1-0.27: Moderate-low
   - 0.27-0.44: Moderate-high
   - > 0.44: High severity
7. Subir thumbnails a `gs://images/episodes/{episode_id}/closure_report/`
8. Marcar `has_closure_report = true` y almacenar `dnbr_mean` en `fire_episodes`

#### Flujos Alternativos

| Escenario | Respuesta | Acción |
|-----------|-----------|--------|
| No hay imagen PRE limpia | Usar fallback -30 días | + warning en metadata |
| Sin POST limpia | Reintentar en siguiente corrida | Max 30 días de reintentos |
| Cloud > 40% | Esperar siguiente corrida | Cloud masking si disponible |

#### Reglas de Negocio

```yaml
Ventanas Temporales:
  imagen_pre:
    preferida: -15 a -7 días desde start_date
    fallback: -30 a -15 días
  imagen_post:
    offset: extinguished_at + 7 días (revegetación inicial)
    max_wait: 30 días

dNBR (Normalized Burn Ratio):
  formula: NBR_pre - NBR_post
  clasificacion:
    low: < 0.1
    moderate_low: 0.1 - 0.27
    moderate_high: 0.27 - 0.44
    high: > 0.44

Ejecución:
  frecuencia: una sola vez por evento
  flag: has_closure_report (evita duplicados)
```

#### Datos y Entidades

- **Tablas**: `fire_events`, `fire_episodes`, `satellite_images`
- **Storage**: `gs://images/episodes/{episode_id}/closure_report/`
- **Worker**: `workers.tasks.imagery.generate_closure_report`

#### Criterios de Aceptación

- [x] Reporte disponible < 24h tras extinción
- [x] No se duplica si ya existe (`has_closure_report = true`)
- [x] dNBR calculado y almacenado
- [x] Reintentos programados si faltan imágenes limpias

---

### UC-F11: Exploración Satelital (Reportes Especializados)

**Estado**: ⏳ En progreso (85% completado)  
**Complejidad**: Muy Alta  
**Prioridad**: P0 (Core Premium)

#### Descripción
Wizard de exploración satelital de 3 pasos que permite observar, comparar y comprender cambios en el terreno afectado por incendios. Genera reportes PDF con evidencia técnica para uso judicial y analítico mediante un flujo guiado con **transparencia de costos** antes de procesar. Cada imagen HD solicitada tiene un costo de U$D 0.50 al usuario. La experiencia está orientada a **investigación, curiosidad y concientización**, no solo a generación de reportes administrativos.

#### Actores
- **Primarios**: Peritos judiciales, fiscales, investigadores, administradores
- **Secundarios**: ERS Service (Evidence Retrieval Service), PDF Service

#### Precondiciones
- `climate_data` cargada para el período del incendio
- GEE operativo
- Usuario con créditos suficientes (sistema de pago MercadoPago)
- `idempotency_keys` habilitado para evitar doble cobro

#### Flujo Principal

**Wizard UX (Frontend - 6 pasos):**
1. **Paso 1: Búsqueda** - Usuario elige incendio vía autocomplete (por provincia, fecha o búsqueda)
2. **Paso 2: Configuración** - Define:
   - Tipo de reporte: `judicial` o `historical`
   - Rango temporal (antes y después del incendio)
   - Número de imágenes deseadas (max 12 para historical)
   - Visualizaciones incluidas (NDVI, NBR, SWIR, RGB)
3. **Paso 3: Preview y Costeo** - Sistema muestra:
   - Cantidad de imágenes a generar
   - Costo total (imágenes × U$D 0.50)
   - Créditos a descontar
   - Estimación de tiempo de generación
4. **Paso 4: Confirmación** - Usuario confirma y procesa pago (MercadoPago)
5. **Paso 5: Polling** - Progreso visible ("Buscando imágenes...", "Generando PDF...") 30-120s
6. **Paso 6: Download** - PDF disponible con hash SHA-256 verificable

**Backend Flow:**
1. Frontend llama `POST /api/v1/explorations/` con `Idempotency-Key` header
2. API valida créditos del usuario (1 crédito = U$D 0.50 por imagen HD)
3. Se crea `investigation` con status `pending` y se retorna `investigation_id`
4. Worker async (Celery) inicia procesamiento:
   - **ERS Service** agrega detecciones, clima, imágenes y metadata
   - Si existe `gee_system_index` en metadata → generar HD on-demand
   - Si no existe metadata → consultar GEE directamente
5. **Judicial**: Incluye cronología, mapa de propagación, fuentes
6. **Histórico**: Max 12 imágenes post-incendio con frecuencia configurable
7. Genera PDF con:
   - Logo ForestGuard + watermark
   - Hash SHA-256 del contenido
   - QR code para verificación pública
   - Disclaimers y limitaciones
8. Guarda PDF en GCS (retención 90 días) y actualiza `investigation.status = 'completed'`
9. Frontend hace polling cada 5s a `GET /api/v1/explorations/{investigation_id}` hasta completion
10. Usuario descarga PDF con hash verificable

#### Flujos Alternativos

| Escenario | Respuesta | Acción |
|-----------|-----------|--------|
| Sin clima | PDF con disclaimer | Continúa sin datos climáticos |
| GEE sin imagen | Reintento 3 veces | Reporte parcial si persiste |
| Créditos insuficientes | `402 Payment Required` | Redirect a `/credits` |
| Duplicate request (mismo Idempotency-Key) | `409 Conflict` | Retorna investigación existente |

#### Reglas de Negocio

```yaml
Costos:
  imagen_hd: 0.50 USD (1 crédito)
  reporte_base: 0 USD (solo imágenes se cobran)

Límites:
  judicial:
    max_imagenes: ilimitado (cobrado)
    incluye: cronología, propagación, fuentes, metadata legal
  historical:
    max_imagenes: 12
    frecuencia_configurable: semanal, quincenal, mensual

PDF:
  hash: SHA-256 del contenido completo
  qr_code: URL pública de verificación
  retention: 90 días en GCS
  formato: A4, orientación portrait

Idempotencia:
  header_required: Idempotency-Key (UUID)
  ttl: 24 horas
  behavior: 409 si duplicado + retorna investigación original
```

#### Datos y Entidades

- **Tablas**: `fire_events`, `fire_detections`, `protected_areas`, `climate_data`, `satellite_images`, `idempotency_keys`, `exploration_investigations`
- **Schemas**: `JudicialReportRequest`, `HistoricalReportRequest`, `InvestigationResponse`

#### Endpoints

```http
POST /api/v1/explorations/
Content-Type: application/json
Authorization: Bearer <jwt_token>
Idempotency-Key: <uuid>

Body:
{
  "fire_event_id": "uuid",
  "investigation_type": "historical",
  "config": {
    "max_images": 12,
    "frequency": "weekly",
    "include_ndvi": true,
    "include_climate": true
  }
}

Response (202 Accepted):
{
  "investigation_id": "uuid",
  "status": "pending",
  "estimated_cost_usd": 6.00,  # 12 imágenes × $0.50
  "credits_charged": 12,
  "estimated_completion_seconds": 90
}

# Polling endpoint
GET /api/v1/explorations/{investigation_id}

Response (200):
{
  "investigation_id": "uuid",
  "status": "completed",  # pending | processing | completed | failed
  "progress_percent": 100,
  "pdf_url": "https://storage.googleapis.com/.../report_abc123.pdf",
  "pdf_hash": "sha256:def456...",
  "verification_url": "https://forestguard.app/verify/report_abc123",
  "created_at": "2024-02-09T18:30:00Z",
  "completed_at": "2024-02-09T18:32:15Z"
}
```

#### Criterios de Aceptación

- [x] PDF incluye fuentes, hash y limitaciones
- [x] Generación en cola con estado consultable (polling)
- [ ] HD on-demand (no se almacena permanentemente) - **Pendiente**
- [x] Idempotencia funcional (no doble cobro)
- [x] QR code verificable públicamente

#### Experiencia de Usuario (UX)

**Narrativa:** Exploración e investigación guiada (no "reportes administrativos")

**Transparencia:**
- Costeo explícito antes de procesar (paso 3 del wizard)
- Estimación de tiempo visible durante polling
- Costos desglosados por imagen

**Comparación Temporal:**
- Antes/durante/después del incendio
- Selección de visualizaciones: NDVI, NBR, SWIR, RGB
- Timeline slider para navegación temporal

**Features de Exploración:**
- Wizard guiado de 6 pasos
- Comparador before/after tipo slider
- Gráfico NDVI time series
- Exportación a PDF con metadatos completos

**Descarga:**
- PDF con hash SHA-256 verificable
- QR code para autenticación pública
- Retention: 90 días en GCS

---

### UC-F13: Agrupación Macro y Gestión de Imágenes Reproducibles

**Estado**: ✅ Implementado  
**Complejidad**: Muy Alta  
**Prioridad**: P0 (Core Optimization)

#### Descripción
Reduce requests a GEE y optimiza storage almacenando solo thumbnails + metadata reproducible. Agrupa detecciones en "episodios" usando clustering espacial-temporal (ST-DBSCAN).

#### Actores
- **Primarios**: Sistema (ETL/Worker de clustering)
- **Secundarios**: Servicios de reportes e imágenes (reutilizan metadata)

#### Precondiciones
- Tablas `fire_events` y `fire_detections` pobladas
- Tabla `fire_episodes` y `fire_episode_events` (N:M) creadas
- Acceso a GEE y GCS
- Parámetros de clustering en `clustering_versions`

#### Flujo Principal
1. **Trigger**: Celery Beat ejecuta daily (03:00 UTC) o ventana temporal configurada (ej: 90 días)
2. Cargar eventos en ventana temporal desde última corrida
3. **Clustering ST-DBSCAN**:
   - Parámetros: `eps_spatial = 5000m`, `eps_temporal = 7 días`, `min_samples = 2`
   - Agrupar por proximidad espacial + continuidad temporal
4. Crear/actualizar `fire_episodes`:
   - Calcular centroide agregado
   - Calcular `start_date`, `end_date` del episodio
   - Métricas agregadas: `total_detections`, `max_frp`, `total_area_hectares`
5. Crear relaciones N:M en `fire_episode_events` (un evento puede pertenecer a múltiples episodios si se requiere overlap)
6. Para cada episodio SIN metadata GEE:
   - Obtener mejor imagen Sentinel-2 (menor nubosidad en ventana)
   - Generar thumbnail (512x512px WebP)
   - **Guardar metadata reproducible**:
     - `gee_system_index` (permite regenerar HD on-demand)
     - `bands_config` (JSON con bandas y parámetros de visualización)
     - `cloud_coverage_pct`
     - `acquisition_date`
7. Subir thumbnail a `gs://images/episodes/{episode_id}/`
8. Marcar episodio con `has_gee_metadata = true`

#### Flujos Alternativos

| Escenario | Respuesta | Acción |
|-----------|-----------|--------|
| Sobre-agregación (episodio muy grande) | Ajustar parámetros | Recalcular con `eps_spatial` menor |
| Sin imagen válida | Marca episodio sin evidencia | `has_gee_metadata = false` |
| Parámetros de clustering cambian | Crear nueva versión | `clustering_versions.version++` |

#### Reglas de Negocio

```yaml
ST-DBSCAN Parameters (versionados):
  eps_spatial: 5000 m  # distancia máxima entre eventos
  eps_time: 7 días     # ventana temporal
  min_samples: 2       # mínimo de eventos para episodio

Relación N:M:
  - Evento original NO se modifica
  - Múltiples episodios pueden compartir eventos (intersección temporal)
  - Trazabilidad completa via fire_episode_events

Metadata Reproducible (satellite_images):
  - gee_system_index: str (ej: "20240315T141234_20240315T141234_T20JLK")
  - bands_config: jsonb (ej: {"vis": "SWIR", "min": 0, "max": 3000})
  - cloud_coverage_pct: float
  - acquisition_date: timestamp

Storage Strategy:
  - Thumbnails: persistentes (WebP 512x512px)
  - HD images: on-demand usando gee_system_index
  - Retention: thumbnails indefinidos, HD se genera y descarta
```

#### Datos y Entidades

- **Tablas**: `fire_detections`, `fire_events`, `fire_episodes`, `fire_episode_events`, `satellite_images`, `clustering_versions`
- **Storage**: `gs://images/episodes/{episode_id}/`
- **Worker**: `workers.tasks.clustering.cluster_episodes`

#### Criterios de Aceptación

- [x] Reducción significativa de requests GEE (estimado 60% menos)
- [x] Trazabilidad N:M entre episodios y eventos
- [x] Metadata suficiente para reproducir imagen HD
- [x] Parámetros versionados (permite recalcular históricos)

---

## 3. Casos de Uso Fuera de MVP

### UC-F07: Registro de Visitantes Offline

**Estado**: ❌ No considerado para MVP  
**Razón**: Requiere infraestructura móvil offline (PWA + sync) y tablas adicionales (`shelters`, `visitor_logs`) fuera del alcance actual.

---

### UC-F10: Certificados (Exploración Visual de Evidencia)

**Estado**: ⚠️ Redefinido - No considerado para MVP inicial, evolucionó en alcance  
**Razón original**: Requiere integración con plataforma de certificados digitales (blockchain/firma digital) y modelo de negocio B2B aún no validado.

**Nueva visión (Post-MVP)**: Centro de exploración visual y descarga de evidencia satelital con flujo guiado.

#### Descripción (evolución de enfoque)

**Cambio de paradigma:**
- **De:** Certificación legal monetizada con firma digital
- **A:** Centro de exploración visual para investigación con hasta 12 imágenes full HD seleccionables

**Nuevo enfoque:**
Permite a cualquier persona (sin conocimientos técnicos) seleccionar hasta 12 imágenes full HD de un área afectada por incendios, comparar el antes/durante/después para "ver con sus propios ojos" qué ocurrió, y descargar un PDF con las imágenes elegidas y un reporte integral (clima, vegetación, uso del suelo) por cada imagen.

#### Flujo Guiado Propuesto

1. **Selección del área:**
   - Buscar lugar / marcar en mapa
   - Definir perímetro de análisis

2. **Selección de fechas/imágenes:**
   - Timeline con hitos ("pre-incendio", "post 3 meses", "post 1 año")
   - Máximo 12 imágenes
   - Feedback inmediato ("8 de 12 seleccionadas")

3. **Vista previa y resumen:**
   - Comparador before/after tipo slider
   - "Qué incluye el PDF" (lista simple)
   - Fuentes utilizadas (logos y breve descripción)

4. **Generación y descarga del PDF:**
   - PDF personalizable armado con lo que el usuario eligió
   - Documento que cuenta una historia (antes/durante/después)
   - Indicadores adjuntos: vegetación saludable, estrés hídrico, cicatriz del incendio

#### Narrativa UX

**Lenguaje:**
- Traducir jerga técnica a conceptos: "vegetación", "humedad", "cambios en el suelo"
- Lo técnico queda como "ver detalle" o tooltip

**Micro-momentos de aprendizaje:**
- Explicaciones cortas (tooltips / "¿qué estoy viendo?")
- Etiquetas con significado humano
- Comparaciones visuales simples

**Confianza por transparencia:**
- Fuentes utilizadas claramente identificadas
- Limitaciones comunicadas ("Qué puede variar": nubosidad, disponibilidad de escena)
- Datos reproducibles y consistentes

#### Diferencia con UC-F11

| Aspecto | UC-F10 Certificates | UC-F11 Exploración Satelital |
|---------|---------------------|------------------------------|
| **Enfoque** | Exploración visual educativa | Reportes técnicos/judiciales |
| **Límite imágenes** | 12 máximo | Ilimitado (judicial) / 12 (historical) |
| **Output** | PDF personalizable visual | PDF con evidencia técnica completa |
| **Público** | Público general, educación | Peritos, fiscales, profesionales |
| **Costo** | Por definir en Post-MVP | U$D 0.50 por imagen HD |
| **Narrativa** | Curiosidad y concientización | Análisis técnico y legal |

#### Roadmap

**Post-MVP (Q3-Q4 2026)**
- Implementación del flujo de selección de imágenes
- Comparador before/after interactivo
- Generación de PDF personalizable
- Integración con sistema de créditos (si aplica)

---

### UC-F12: Recuperación y Cambio de Uso (VAE)

**Estado**: ❌ No considerado para MVP  
**Razón**: Análisis de Vegetation Activity Endpoints (VAE) usando NDVI time series requiere procesamiento pesado y modelo ML para clasificación de cambios de uso del suelo.

**Roadmap**: Post-MVP (Q3-Q4 2026)

---

## 4. Matriz de Casos de Uso vs Endpoints

| Caso de Uso | Endpoints | Auth | Método | Status |
|-------------|-----------|------|--------|--------|
| **UC-F01** | `/api/v1/contact` | ❌ | POST | ✅ |
| **UC-F02** | `/functions/v1/public-stats` | ❌ | GET | ✅ |
| **UC-F03** | `/api/v1/fires`<br>`/api/v1/fires/stats`<br>`/api/v1/fires/export` | ✅ | GET | ✅ |
| **UC-F04** | `/api/v1/quality/{fire_id}` | ✅ | GET | ✅ |
| **UC-F05** | `/api/v1/analysis/recurrence`<br>`/api/v1/analysis/trends` | ✅ | GET | ✅ |
| **UC-F06** | `/api/v1/audit/land-use` | ✅ | POST | ✅ (Verify Land UI) |
| **UC-F08** | (Worker task) | — | — | ✅ |
| **UC-F09** | (Worker task) | — | — | ✅ |
| **UC-F11** | `/api/v1/explorations/`<br>`/api/v1/explorations/{id}` | ✅ | POST/GET | ⏳ (Satellite Exploration) |
| **UC-F13** | (Worker task) | — | — | ✅ |

---

## 5. Restricciones Transversales

### 5.1 FinOps

```yaml
GEE Quotas:
  requests_per_day: 50,000
  concurrent_requests: 40
  eecu_per_month: 150 horas

Supabase:
  database_size: 500 MB (actual: ~280 MB)
  egress: unlimited
  auth_users: 50,000

Google Cloud Storage:
  storage: 5 GB (actual: ~2.3 GB)
  class_a_ops: 5,000/month (uploads)
  class_b_ops: 50,000/month (downloads)

Strategy:
  - Thumbnails persistentes (WebP comprimido)
  - HD on-demand (no persistir)
  - Metadata reproducible (gee_system_index)
  - Archivado a Parquet tras 90 días
```

### 5.2 Seguridad

```yaml
Exposición Pública:
  - Solo agregados vía Edge Function/RPC
  - Rol anon SIN acceso directo a tablas
  - PostgREST cerrado para anon

Rate Limiting:
  contact: 10 req/min por IP
  public_stats: 100 req/min por IP
  audit: 20 req/hora por usuario autenticado

Idempotencia:
  endpoints_criticos: [/reports/judicial, /reports/historical, /audit/land-use]
  header: Idempotency-Key (UUID)
  ttl: 24 horas

Row Level Security (RLS):
  - Todas las tablas sensibles
  - Policies por rol (anon, authenticated, service_role)
```

### 5.3 Retención y Lifecycle

```yaml
Imágenes:
  thumbnails: indefinido (WebP persistentes)
  hd_images: on-demand (generar y descartar)
  formato: WebP (compresión 80%)

PDFs:
  reportes_usuario: 90 días en GCS
  certificados: 365 días (si UC-F10 se implementa)

Datos en BD:
  fire_detections: archivado a Parquet tras 90 días
  audit_logs: indefinido (append-only, compliance legal)
  idempotency_keys: 24 horas TTL

GCS Lifecycle Policy:
  - Nearline tras 90 días (reportes)
  - Delete tras 365 días (thumbnails antiguos)
```

---

**Documento actualizado**: Febrero 2026  
**Próxima revisión**: Post-implementación de UC-F11 completo  
**Mantenedor**: Product Owner + Tech Lead  
**Estado**: 🟢 85% completado
