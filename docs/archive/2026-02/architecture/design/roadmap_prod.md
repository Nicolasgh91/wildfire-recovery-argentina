# ForestGuard - Análisis de proyecto y hoja de ruta para producción

**Documento técnico para agente de código**  
**Fecha:** 2026-02-10  
**Versión:** 5.0

---

## 1. Resumen ejecutivo

El proyecto ForestGuard se encuentra en un estado avanzado con el 68% de las tareas completadas. Las fases críticas de infraestructura (tablas, modelo, API y workers) están finalizadas. Quedan pendientes las tareas de hardening de seguridad, el módulo de exploración satelital y testing.

### 1.1 Métricas actuales

| Métrica | Valor | Observación |
|---------|-------|-------------|
| Tareas completadas | 21 / 31 | 68% del total |
| Casos de uso MVP | 9 / 10 | Solo falta UC-F11 (exploración) |
| Días trabajados (est.) | ~22 días | Según roadmap |
| Días restantes (est.) | ~24 días | Para producción |
| Score arquitectónico | 5.8 / 10 | Objetivo: 10/10 post-hardening |

### 1.2 Próximos pasos inmediatos

1. **Ejecutar tareas P0 de seguridad** (~30 min): hard caps, CORS, sanitización PII
2. **Completar tareas P1** (~6.5 h): RLS, rate limiting, índices
3. **Desarrollar UC-F11** (4 días): wizard de exploración satelital
4. **Testing E2E** (6 días): cobertura >80%, tests de integración

---

## 2. Estado de casos de uso

### 2.1 Casos de uso MVP

| ID | Nombre | Estado | Notas |
|----|--------|--------|-------|
| UC-F01 | Contacto y soporte | ✅ Completado | Endpoint POST /api/v1/contact operativo |
| UC-F02 | Estadísticas públicas agregadas | ✅ Completado | Edge Function con RPC |
| UC-F03 | Histórico de incendios y dashboard | ✅ Completado | Dashboard con filtros y exportación |
| UC-F04 | Calidad y confiabilidad del dato | ✅ Completado | Score de calidad operativo |
| UC-F05 | KPIs de recurrencia y tendencias | ✅ Completado | Análisis H3 con vistas materializadas |
| UC-F06 | Auditoría legal de uso del suelo | ✅ Completado | Endpoint /api/v1/audit/land-use |
| UC-F08 | Carrusel de imágenes | ✅ Completado | MVP thumbnails locales |
| UC-F09 | Reporte de cierre pre/post incendio | ✅ Completado | Worker closure_report |
| UC-F11 | Exploración satelital | ⏳ Pendiente | Wizard de 3 pasos pendiente |
| UC-F13 | Agrupación macro y gestión de imágenes | ✅ Completado | Worker clustering de episodios |

### 2.2 Casos de uso post-MVP

| ID | Nombre | Estado | Notas |
|----|--------|--------|-------|
| UC-F07 | Visitantes y refugios | ❌ Post-MVP | Requiere nuevas tablas |
| UC-F10 | Certificación legal monetizada | ❌ Post-MVP | Integración MercadoPago |
| UC-F12 | Recuperación y cambio de uso (VAE) | ❌ Post-MVP | Monitoreo NDVI post-incendio |

---

## 3. Progreso por fases

### 3.1 Fases completadas

| Fase | Nombre | Tareas | Completadas | Progreso |
|------|--------|--------|-------------|----------|
| Fase 0 | Tablas base faltantes | 3 | 3 | 100% ✅ |
| Fase 1 | Modelo y persistencia | 8 | 8 | 100% ✅ |
| Fase 2 | API y lógica MVP | 6 | 6 | 100% ✅ |
| Fase 3 | Workers e imágenes | 4 | 4 | 100% ✅ |

### 3.2 Fases pendientes

| Fase | Nombre | Tareas | Días estimados |
|------|--------|--------|----------------|
| Fase 4 | Hardening y seguridad | 3 | 7 días |
| Fase 5 | Exploración y reportes | 3 | 10 días |
| Fase 6 | Testing y observabilidad | 4 | 7 días |

---

## 4. Hoja de ruta para producción

El camino crítico para llevar la aplicación a producción consta de 3 semanas de trabajo estructurado.

### 4.1 Cronograma visual

```
SEMANA 1: Seguridad y performance (~13 h)
├── SEC-001 a SEC-012: hardening de seguridad
└── PERF-001 a PERF-006: índices y vistas materializadas

SEMANA 2: Resiliencia y accionabilidad (~10 h)
├── RES-001 a RES-005: circuit breaker, health checks, DLQ
└── ACT-001 a ACT-004: rollback, boundary tests

SEMANA 3: Exploración y testing (~15 h)
├── T5.1 a T5.3: wizard exploración, series históricas, PDF
└── T6.1 a T6.4: tests unitarios, integración, E2E, monitoreo
```

---

## 5. Tareas técnicas detalladas

> **INSTRUCCIONES PARA EL AGENTE DE CÓDIGO:**
> 1. Ejecutar tareas en orden de prioridad (P0 → P1 → P2 → P3)
> 2. Cada tarea debe completarse antes de pasar a la siguiente
> 3. Verificar criterios de aceptación después de cada cambio
> 4. Crear commits atómicos con mensajes descriptivos

### 5.1 Tareas P0 - Críticas (implementar HOY)

**Branch recomendado:** `fix/security-hardening-p0`

| ID | Tarea | Archivo | Tiempo |
|----|-------|---------|--------|
| SEC-001 ✅ | Hard cap en paginación de transacciones | app/api/v1/payments.py:308 | 5 min |
| SEC-002 ✅ | CORS con configuración por ambiente | app/core/config.py:50 | 10 min |
| SEC-003 ✅ | Hard cap en export de incendios | app/api/v1/fires.py:235 | 5 min |
| SEC-004 ✅ | Sanitizar PII en logs | app/core/sanitizer.py (nuevo) | 30 min |
| SEC-005 ✅ | Limpiar .env.template | .env.template:38 | 2 min |

### 5.2 Tareas P1 - Prioridad alta (esta semana)

| ID | Tarea | Archivo | Tiempo |
|----|-------|---------|--------|
| SEC-006 ✅ | Verificar RLS en Supabase | Supabase Dashboard | 30 min |
| SEC-007 ✅ | Rate limiting en auth | app/api/v1/auth.py | 45 min |
| SEC-008 ✅ | Webhook replay protection | app/api/v1/webhooks.py | 1 h |
| PERF-001 ✅ | Índices GIST para queries espaciales | migrations/ | 30 min |
| PERF-002 ✅ | Migración vista materializada h3_recurrence_stats | migrations/ | 1 h |
| IDMP-001 ✅ | Idempotency keys en reportes | app/api/routes/reports.py | 1 h |

### 5.3 Tareas P2 - Prioridad media (próxima semana)

| ID | Tarea | Archivo | Tiempo |
|----|-------|---------|--------|
| RES-001 ✅ | Circuit breaker para GEE | app/services/gee_service.py | 2 h |
| RES-002 ✅ | Health checks granulares | app/api/routes/health.py | 1 h |
| RES-003 ✅ | Dead letter queue para workers | app/workers/ | 1.5 h |
| DOC-001 ✅ | Docstrings en servicios core | app/services/ | 2 h |

### 5.4 Fase 5: exploración y reportes (UC-F11)

Esta fase implementa el wizard de 3 pasos para exploración de imágenes satelitales. Es el único caso de uso MVP pendiente.

| ID | Tarea | Dependencias | Tiempo |
|----|-------|--------------|--------|
| T5.1 | Wizard exploración satelital (3 pasos) | T3.1, T3.4 | 4 días |
| T5.2 | Visualización series históricas | T5.1 | 3 días |
| T5.3 | Generación PDF con hash y QR | T5.1, T5.2 | 3 días |

#### Especificación T5.1: wizard exploración satelital

**Paso 1 - Búsqueda:**
- Usuario ingresa coordenadas o selecciona área en mapa
- Sistema muestra fire_events en el área (sin costo)
- Usuario selecciona evento(s) a explorar

**Paso 2 - Selección de período:**
- Usuario define rango temporal (pre/post incendio)
- Sistema calcula cantidad de imágenes disponibles
- Máximo 12 imágenes por reporte histórico

**Paso 3 - Confirmación y costeo:**
- Sistema muestra costo total (ARS por imagen según pricing backend)
- Usuario confirma pago antes de procesar
- Sistema genera job asíncrono y retorna tracking ID

### 5.5 Fase 6: testing y observabilidad

| ID | Tarea | Dependencias | Tiempo |
|----|-------|--------------|--------|
| T6.1 | Tests unitarios (80% coverage) | Fases 1-5 | 2 días |
| T6.2 | Tests de integración | T6.1 | 2 días |
| T6.3 | Tests E2E (flujos críticos) | T6.2 | 2 días |
| T6.4 | Monitoreo y alertas | - | 1 día |

**Estado:** ✅ COMPLETADO (T6.1–T6.4)

#### Plan de acción Fase 6

**T6.1 Tests unitarios (pytest + vitest)**
- Backend: unit tests para `app/api/v1/audit.py` y validación de `mode` en `app/api/routes/episodes.py`.
- Frontend: vitest + RTL para Home (toggle, fallback, empty state) y mapeo de items (centroid + `representative_event_id`).

**T6.2 Tests de integración (pytest)**
- Casos: `GET /api/v1/fire-episodes?mode=active|recent`, `mode` inválido → 400, `GET /api/v1/audit/search` por provincia/área/dirección (404 si no hay match).

**T6.3 Tests E2E (Playwright)**
- Flujos críticos en `frontend/tests/ui/`: Home toggle, Mapa con marcadores, Audit con resultados.

**T6.4 Monitoreo y alertas (hardening plan)**
- Implementar OBS-001 a OBS-004 según `docs/architecture/Refactor/security/2_hardening_plan_score_10.md`.
- Documentar `/metrics` como endpoint interno y definir SLOs en `docs/slos.md`.

### 5.6 Ajustes UI/UX (Activos + Recientes + Home/Mapa/Audit)

**Objetivo:** Evitar Home vacía y mostrar episodios recientes cuando no hay activos, reemplazar datos mock en el mapa y habilitar búsqueda histórica en Audit.

**Resumen de cambios implementados:**
- Backend: `GET /api/v1/fire-episodes` con `mode=active|recent`.
- Backend: `representative_event_id` y centroides para mapear episodios.
- Frontend Home: toggle “Ver recientes”, fallback automático y dedupe.
- Frontend Mapa: episodios reales (activos + recientes) con marcadores por centroide.
- Backend Audit: `GET /api/v1/audit/search` con resolución de lugar.
- Frontend Audit: tarjeta de lugar resuelto + listado histórico.

| ID | Tarea | Estado |
|----|-------|--------|
| UIX-01 | Endpoint `mode=active|recent` en episodios | ✅ Completado |
| UIX-02 | Home con toggle y fallback recientes | ✅ Completado |
| UIX-03 | Mapa con episodios reales y centroides | ✅ Completado |
| UIX-04 | Audit search (backend + UI) | ✅ Completado |

---

## 6. Detalles de implementación por tarea

### 6.1 SEC-001: hard cap en paginación

**Archivo:** `app/api/v1/payments.py:308`

```python
# ANTES
page_size: int = 20,

# DESPUÉS
page_size: int = Query(20, ge=1, le=100, description="Items per page"),
```

**Verificación:**
- `page_size=100` → 200 OK
- `page_size=101` → 422 Unprocessable Entity

### 6.2 SEC-002: CORS por ambiente

**Archivo:** `app/core/config.py:50`

```python
# ANTES
ALLOWED_ORIGINS: List[str] = ["*"]

# DESPUÉS
ALLOWED_ORIGINS: List[str] = Field(
    default_factory=list,
    description="Must be explicitly configured per environment"
)
```

**Configuración de ambiente:**
- `.env.development`: `["http://localhost:5173","http://localhost:3000"]`
- `.env.production`: `["https://forestguard.app"]`

### 6.3 SEC-003: hard cap en export

**Archivo:** `app/api/v1/fires.py:235`

```python
# ANTES
max_records: Optional[int] = Query(None),

# DESPUÉS
max_records: Optional[int] = Query(
    None, ge=1, le=10000, description="Max records for export. None = server default"
),
```

### 6.4 SEC-004: sanitización de PII

**Crear archivo:** `app/core/sanitizer.py`

```python
import re

_EMAIL_RE = re.compile(r'[\w.-]+@[\w.-]+\.\w+')
_IPV4_RE = re.compile(r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.)\d{1,3}\b')
_JWT_RE = re.compile(r'eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+')


def redact_pii(message: str) -> str:
    """Redact PII from log messages. Ley 25.326 compliance."""
    message = _EMAIL_RE.sub(
        lambda m: m.group()[0] + '***@' + m.group().split('@')[1], message
    )
    message = _IPV4_RE.sub(r'\1***', message)
    message = _JWT_RE.sub('[JWT_REDACTED]', message)
    return message
```

**Verificación:**
```bash
grep -rn "logger\.\(info\|debug\|error\|warning\)" app/ \
  | grep -iE "email|password|token|ip_addr|address" \
  | grep -v "redact_pii\|REDACTED"
# Debe retornar vacío
```

### 6.5 SEC-005: limpiar .env.template

**Archivo:** `.env.template:38`

Reemplazar todos los valores de ejemplo con placeholders:
```bash
DB_PASSWORD=<CHANGE_ME_strong_password>
SECRET_KEY=<CHANGE_ME_random_256bit>
SUPABASE_SERVICE_KEY=<CHANGE_ME_supabase_key>
```

### 6.6 SEC-006: verificación RLS en Supabase

Ejecutar la siguiente query para identificar tablas sin RLS:

```sql
SELECT schemaname, tablename, rowsecurity
FROM pg_tables
WHERE schemaname = 'public' AND NOT rowsecurity;
```

Resultado de verificacion (2026-02-11): tablas sin RLS detectadas:
- clustering_versions
- episode_mergers
- system_parameters
- regions
- fire_protected_area_intersections
- protected_areas
- burn_certificates
- land_use_audits
- land_use_changes
- spatial_ref_sys
- forensic_cases
- recovery_metrics
- alembic_version
- vegetation_monitoring
- fire_stats_refresh_state
- fire_climate_associations
- climate_data
- data_source_metadata

Resultado posterior a habilitar RLS (2026-02-11): solo queda `spatial_ref_sys`
sin RLS (tabla de sistema PostGIS en Supabase).

**Checklist de tablas críticas:**

| Tabla | RLS | Policy anon | Policy authenticated |
|-------|-----|-------------|---------------------|
| fire_events | ☐ verificar | solo SELECT agregado (vía RPC) | SELECT |
| fire_detections | ☐ verificar | sin acceso directo | SELECT |
| audit_logs | ☐ verificar | sin acceso | INSERT only (append) |
| satellite_images | ☐ verificar | sin acceso | SELECT |
| user_saved_filters | ☐ verificar | sin acceso | CRUD own rows |
| idempotency_keys | ☐ verificar | sin acceso | solo service_role |

**Ejemplo de policy para user_saved_filters:**
```sql
ALTER TABLE user_saved_filters ENABLE ROW LEVEL SECURITY;

CREATE POLICY "users_own_filters" ON user_saved_filters
  FOR ALL
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);
```

### 6.7 RES-001: circuit breaker para GEE

**Archivo:** `app/services/gee_service.py`

Implementar patrón circuit breaker con 3 estados:
- **CLOSED:** funcionamiento normal
- **OPEN:** rechaza requests inmediatamente (5 fallos consecutivos)
- **HALF-OPEN:** permite 1 request de prueba cada 60 segundos

**Dependencias:**
```bash
pip install circuitbreaker --break-system-packages
```

**Implementación:**
```python
from circuitbreaker import circuit

@circuit(failure_threshold=5, recovery_timeout=60)
async def call_gee_api(self, params):
    # Llamada a GEE
    pass
```

---

## 7. Camino crítico y dependencias

### Orden de ejecución obligatorio

```
P0 (SEC-001→SEC-005)
    ↓
P1 (SEC-006→IDMP-001)
    ↓
P2 (RES-001→DOC-001)
    ↓
T5.1 (Wizard exploración)
    ↓
T5.2 (Series históricas)
    ↓
T5.3 (PDF con hash/QR)
    ↓
T6.1→T6.2→T6.3 (Testing)
    ↓
✅ PRODUCCIÓN
```

### 7.1 Criterios de éxito

| Métrica | Estado actual | Objetivo |
|---------|---------------|----------|
| Archivos de rutas | 33 | 17 |
| Endpoints duplicados/stub | 10 | 0 |
| Endpoints sin rate limit | 54 | <20 |
| Endpoints sin hard caps | 2 | 0 |
| CORS wildcard | Sí | No |
| Health checks | 1 genérico | 4 (DB, Redis, Celery, GEE) |
| X-Request-ID | No | Sí |
| Test coverage | ~40% | >80% |

---

## 8. Archivos de referencia

| Archivo | Propósito |
|---------|-----------|
| /mnt/project/0_master_plan.md | Plan maestro con análisis de endpoints |
| /mnt/project/1_arquitectura_final.md | Arquitectura del sistema |
| /mnt/project/2_casos_de_uso_final.md | Especificaciones de casos de uso |
| /mnt/project/2_hardening_plan_score_10.md | Plan de hardening detallado |
| /mnt/project/3_technical_roadmap.md | Roadmap técnico unificado |
| /mnt/project/4_casos_de_prueba.md | Casos de prueba por UC |
| /mnt/project/schema_v0_1.sql | Schema base de BD |
| /mnt/project/endpoints_refactor.md | Revisión arquitectónica endpoints |
| /mnt/project/reports_refactor_technical_tasks.md | Tareas de refactor de reportes |

### 8.1 Instrucciones finales para el agente

1. **Leer este documento completo** antes de iniciar cualquier tarea
2. **Consultar** `/mnt/project/2_hardening_plan_score_10.md` para detalles de cada tarea SEC/PERF/RES
3. **Verificar dependencias** en `/mnt/project/3_technical_roadmap.md`
4. **Seguir convenciones** definidas en el código existente
5. **Actualizar estado** de cada tarea al completar
6. **NO inventar** funcionalidades no especificadas
7. **Preguntar** ante cualquier ambigüedad antes de implementar

---

*— Fin del documento —*
