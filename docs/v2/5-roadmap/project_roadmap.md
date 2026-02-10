# ForestGuard - Roadmap del Proyecto v2.0

**Fecha de actualización**: Febrero 2026  
**Versión del roadmap**: 6.0  
**Estado del proyecto**: 85% completado  
**Progreso**: 21/34 tareas técnicas completadas (3 nuevas tareas UI agregadas)

---

## 1. Estado General del Proyecto

### 1.1 Resumen Ejecutivo

ForestGuard es una plataforma de inteligencia geoespacial para fiscalización legal y monitoreo de incendios forestales en Argentina. El proyecto ha completado el 85% de su desarrollo MVP, con **21 de 31 tareas** implementadas exitosamente.

**Hitos principales alcanzados**:
- ✅ Base de datos completa (30+ tablas, 3 vistas materializadas)
- ✅ Backend API (35+ endpoints, 30 servicios)
- ✅ Frontend React (20 páginas, 93 componentes)
- ✅ Autenticación Supabase (Google OAuth + Email OTP)
- ✅ Workers Celery (clustering, carousel, closure, NASA FIRMS)
- ✅ Integración GEE reproducible
- ✅ Sistema de pagos MercadoPago

**Pendiente para MVP**:
- ⏳ Refactoring & Security (T4.1-T4.3)
- ⏳ Exploración Satelital completa (T5.1-T5.3)
- ⏳ Testing & Observabilidad (T6.1-T6.4)

---

## 2. Progreso por Fase

### Visualización General

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          FORESTGUARD PROGRESS OVERVIEW                           │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  FASE 0: Tablas base faltantes          [████████████████████] 100% ✅          │
│  ───────────────────────────────────────────────────────────────────────────    │
│  T0.1 climate_data                      ✅ Completada                           │
│  T0.2 fire_climate_associations         ✅ Completada                           │
│  T0.3 data_source_metadata              ✅ Completada                           │
│                                                                                  │
│  FASE 1: Modelo y persistencia          [████████████████████] 100% ✅          │
│  ───────────────────────────────────────────────────────────────────────────    │
│  T1.1 h3_index en fire_events           ✅ Completada                           │
│  T1.2 clustering_versions               ✅ Completada                           │
│  T1.3 system_parameters                 ✅ Completada                           │
│  T1.4 episode_mergers                   ✅ Completada                           │
│  T1.5 h3_recurrence_stats (MV)          ✅ Completada                           │
│  T1.6 Extensión fire_episodes           ✅ Completada                           │
│  T1.7 user_saved_filters                ✅ Completada                           │
│  T1.8 Extensión satellite_images        ✅ Completada                           │
│                                                                                  │
│  FASE 2: API y lógica MVP               [████████████████████] 100% ✅          │
│  ───────────────────────────────────────────────────────────────────────────    │
│  T2.1 Contacto UC-F01                   ✅ Completada                           │
│  T2.2 Edge Function UC-F02              ✅ Completada                           │
│  T2.3 Fire Service UC-F03               ✅ Completada                           │
│  T2.4 Quality Service UC-F04            ✅ Completada                           │
│  T2.5 Análisis H3 UC-F05                ✅ Completada                           │
│  T2.6 Auditoría legal UC-F06            ✅ Completada                           │
│                                                                                  │
│  FASE 3: Workers e imágenes             [████████████████████] 100% ✅          │
│  ───────────────────────────────────────────────────────────────────────────    │
│  T3.1 Episode Worker UC-F13             ✅ Completada                           │
│  T3.2 Carousel Worker UC-F08            ✅ Completada                           │
│  T3.3 Closure Worker UC-F09             ✅ Completada                           │
│  T3.4 Refresh Endpoint                  ✅ Completada                           │
│                                                                                  │
│  FASE 4: Refactoring & Security         [░░░░░░░░░░░░░░░░░░░░] 0% ⏳            │
│  ───────────────────────────────────────────────────────────────────────────    │
│  T4.1 Security Hardening                ⏳ Pendiente                            │
│  T4.2 Performance & Docs                ⏳ Pendiente                            │
│  T4.3 Resilience & Cleanup              ⏳ Pendiente                            │
│                                                                                  │
│  FASE 5: Exploración & Reportes         [░░░░░░░░░░░░░░░░░░░░] 0% ⏳            │
│  ───────────────────────────────────────────────────────────────────────────    │
│  T5.1 Exploración Satelital             ⏳ Pendiente                            │
│  T5.2 Reportes Históricos               ⏳ Pendiente                            │
│  T5.3 PDF con hash y QR                 ⏳ Pendiente                            │
│  T5.4 Refactor Landing Page             ⏳ Pendiente (Nueva)                  │
│  T5.5 Refactor Verify Land              ⏳ Pendiente (Nueva)                  │
│  T5.6 Refactor Certificates             ⏳ Pendiente (Nueva)                  │
│                                                                                  │
│  FASE 6: Testing & Observabilidad       [░░░░░░░░░░░░░░░░░░░░] 0% ⏳            │
│  ───────────────────────────────────────────────────────────────────────────    │
│  T6.1 Tests unitarios (80% coverage)    ⏳ Pendiente                            │
│  T6.2 Tests de integración              ⏳ Pendiente                            │
│  T6.3 Tests E2E (flujos críticos)       ⏳ Pendiente                            │
│  T6.4 Monitoreo y alertas               ⏳ Pendiente                            │
│                                                                                  │
│  ═══════════════════════════════════════════════════════════════════════════    │
│  PROGRESO TOTAL:  21 / 34 tareas completadas (62%)                              │
│  ═══════════════════════════════════════════════════════════════════════════    │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Tareas Completadas (21 tareas)

### FASE 0: Tablas Base (3/3)✅

| ID | Tarea | UC | Fecha | Descripción |
|----|-------|-----|-------|-------------|
| T0.1 | `climate_data` | UC-F04 | 2026-02-03 | Tabla de datos climáticos (OpenMeteo) |
| T0.2 | `fire_climate_associations` | UC-F04 | 2026-02-03 | Relación N:M incendios-clima |
| T0.3 | `data_source_metadata` | UC-F04 | 2026-02-03 | Metadata de fuentes (NASA, GEE, etc.) |

---

### FASE 1: Modelo y Persistencia (8/8) ✅

| ID | Tarea | UC | Descripción |
|----|-------|-----|-------------|
| T1.1 | `h3_index` en fire_events | UC-F05 | Columna BIGINT para H3 resolution 7-9 |
| T1.2 | `clustering_versions` | UC-F13 | Versionado de parámetros ST-DBSCAN |
| T1.3 | `system_parameters` | Varios | Hard caps configurables (API, GEE, etc.) |
| T1.4 | `episode_mergers` | UC-F13 | Tracking de fusiones de episodios |
| T1.5 | `h3_recurrence_stats` (MV) | UC-F05 | Vista materializada para análisis H3 |
| T1.6 | Extensión `fire_episodes` | UC-F09/13 | Columnas `dnbr`, `clustering_version_id` |
| T1.7 | `user_saved_filters` | UC-F03 | Guardado de filtros de dashboard |
| T1.8 | Extensión `satellite_images` | UC-F08/11 | `gee_system_index`, `visualization_params` |

**Logros clave**:
- Soporte completo para análisis H3 de recurrencia
- Reproducibilidad de imágenes GEE vía metadata
- Configuración dinámica sin redeploy

---

### FASE 2: API y Lógica MVP (6/6) ✅

| ID | Tarea | UC | Endpoints | Descripción |
|----|-------|-----|-----------|-------------|
| T2.1 | Contacto | UC-F01 | `POST /api/v1/contact` | Formulario de contacto con SMTP |
| T2.2 | Edge Function Stats | UC-F02 | `GET /functions/v1/public-stats` | Estadísticas públicas agregadas |
| T2.3 | Fire Service | UC-F03 | `GET /api/v1/fires/*` | Dashboard e histórico de incendios |
| T2.4 | Quality Service | UC-F04 | `GET /api/v1/quality/{fire_id}` | Score de confiabilidad |
| T2.5 | Análisis H3 | UC-F05 | `GET /api/v1/analysis/recurrence` | Recurrencia y tendencias |
| T2.6 | Auditoría Legal | UC-F06 | `POST /api/v1/audit/land-use` | Consulta de restricciones legales |

**Logros clave**:
- API REST completa para casos de uso MVP
- Validación Pydantic v2 estricta
- Rate limiting por endpoint

---

### FASE 3: Workers e Imágenes (4/4) ✅

| ID | Tarea | UC | Worker | Descripción |
|----|-------|-----|--------|-------------|
| T3.1 | Episode Worker | UC-F13 | Clustering | ST-DBSCAN espacial-temporal diario |
| T3.2 | Carousel Worker | UC-F08 | Carousel | Thumbnails GEE para incendios activos |
| T3.3 | Closure Worker | UC-F09 | Closure | Reportes pre/post con dNBR |
| T3.4 | Refresh Endpoint | UC-F08 | - | `POST /api/v1/imagery/refresh/{fire_id}` |

**Logros clave**:
- Procesamiento async con Celery Beat
- Batch processing GEE (15 incendios/corrida)
- Priorización ponderada (PA proximity, FRP, área)

---

## 4. Tareas Pendientes (10 tareas)

### FASE 4: Refactoring & Security (0/3) - **Prioridad P0/P1**

#### T4.1: Security Hardening (P0)

**Estimación**: 2 días  
**Prioridad**: 🔴 Alta

**Descripción**: Implementación de hard caps, sanitización de logs y seguridad en CORS.

**Subtareas**:
```
SEC-001: Hard cap en page_size (max 100) y max_records (max 10000)
  - Modificar schemas/common.py para validar límites
  - Agregar check en middleware
  
SEC-002: Configuración estricta de CORS por ambiente
  - settings.ALLOWED_ORIGINS debe ser lista explícita
  - No wildcards en producción
  
ROB-002: Sanitización de PII en logs
  - Scrubbing de emails, IPs, tokens
  - Implementar LogFilter custom
```

**Artefactos**:
- `app/core/security.py` (actualizar)
- `app/core/middleware.py` (añadir PII scrubber)
- `app/schemas/common.py` (validators)

---

#### T4.2: Performance & Documentación (P1)

**Estimación**: 2 días  
**Prioridad**: 🟡 Media

**Descripción**: Mejoras de performance en BD y documentación técnica.

**Subtareas**:
```
PERF-001: Verificar índices GIST en columnas geométricas
  - fire_events.centroid
  - fire_events.perimeter
  - protected_areas.geometry
  
PERF-002: Optimizar refresh de MV h3_recurrence_stats
  - Configurar Celery Beat para refresh diario 02:00 ART
  - Crear índice único en h3_index
  
DOC-001: Docstrings en servicios core
  - FireService, ERSService, GEEService, VAEService
  - Formato Google Style
```

**Artefactos**:
- `database/migrations/025_add_gist_indexes.sql`
- Docstrings en `app/services/`

---

#### T4.3: Resilience & Cleanup (P2)

**Estimación**: 3 días  
**Prioridad**: 🟢 Baja

**Descripción**: Limpieza de deuda técnica y verificación de resiliencia.

**Subtareas**:
```
TEST-001: Unit tests coverage > 80%
  - Tests para services layer
  - Tests para utils (spatial, h3, validators)
  
IDMP-001: Idempotency keys en reportes
  - Tabla idempotency_keys
  - Middleware de deduplicación
  - TTL 24 horas
```

**Artefactos**:
- `tests/unit/services/`
- `database/migrations/026_idempotency_keys.sql`
- `app/core/middleware.py` (idempotency middleware)

---

### FASE 5: Exploración & Reportes (0/3)

#### T5.1: Exploración Satelital (UC-F11 Rediseño)

**Estimación**: 4 días  
**Prioridad**: 🔴 Alta

**Descripción**: Wizard de 3 pasos para exploración de imágenes: Búsqueda, Selección de Período y Costeo.

**Decisiones validadas**:
- **Zero Cost Start**: Solo mapa y perímetros al inicio
- **Paywall explícito**: Confirmación de costo GEE antes de procesar
- **User Tone**: "Investigación" en lugar de "Reporte Legal"

**Wizard Steps**:
1. **Búsqueda**: Selección de incendio (autocomplete)
2. **Configuración**: Tipo de reporte, rango temporal, visualizaciones
3. **Preview & Cost**: Muestra créditos a cobrar
4. **Confirmación**: Procesa pago + dispara Celery worker
5. **Polling**: Muestra progreso (30-120s)
6. **Download**: PDF con hash SHA-256

**Endpoints**:
```
POST /api/v1/explorations/
GET  /api/v1/explorations/{id}
GET  /api/v1/explorations/
```

**Artefactos**:
- `frontend/src/pages/Exploration.tsx` (refactor)
- `app/api/v1/explorations.py`
- `app/services/exploration_service.py`

---

#### T5.2: Reportes Históricos (UC-F11 parte 2)

**Estimación**: 3 días  
**Prioridad**: 🔴 Alta

**Descripción**: Visualización de series históricas y comparador "Antes/Después".

**Features**:
- Timeline slider con imágenes satelitales
- Comparador side-by-side
- Gráfico NDVI time series
- Exportar a PDF

**Dependencias**: T5.1

**Artefactos**:
- `frontend/src/components/exploration/TimelineSlider.tsx`
- `frontend/src/components/exploration/ImageComparator.tsx`

---

#### T5.3: Generación de PDF con hash y QR

**Estimación**: 3 días  
**Prioridad**: 🟡 Media

**Descripción**: Servicio de generación de PDFs verificables con QR.

**Especificaciones**:
- Template Jinja2 con branding ForestGuard
- Hash SHA-256 del contenido completo
- QR code con URL de verificación pública
- Metadata: usuario, fecha, número de certificado
- Retención GCS: 90 días

**Endpoint de verificación**:
```
GET /api/v1/reports/{report_number}/verify
  Response: { valid: bool, hash_match: bool, metadata: {...} }
```

**Dependencias**: T5.1, T5.2

**Artefactos**:
- `app/services/pdf_service.py`
- `app/templates/report_template.html.j2`
- `app/utils/qr_utils.py`

---

#### T5.4: Refactor Landing Page (Nueva)

**Estimación**: 2 días  
**Prioridad**: 🟡 Media

**Descripción**: Nueva página de login/landing con mejoras UX para aumentar claridad, confianza y motivación del usuario no técnico.

**Objetivo**: Primera impresión clara, accesible y orientada a curiosidad e investigación ("evidencia desde el espacio").

**Features UI/UX:**
- Layout en 2 columnas (mensaje + login | imagen lateral)
- Fondo blanco profesional (modo claro)
- Animación premium del título (revelado tipo "tinta")
- Formulario minimalista y liviano
- Copy estratégico orientado a investigación
- Imagen lateral como "ventana al territorio"

**Principios aplicados:**
- Claridad antes que espectacularidad
- Confianza por diseño (lenguaje visual sobrio)
- Jerarquía fuerte (título dominante, subtítulo explicativo)
- Accesibilidad y legibilidad (contraste, espaciado, tipografía moderna)

**Copy exacto:**
- H1: "ForestGuard" con efecto revelado
- Subtítulo: "Evidencia satelital para entender qué pasó con el territorio después de un incendio"
- Controles AAA: `prefers-reduced-motion` para accesibilidad

**Artefactos:**
- `frontend/src/pages/Landing.tsx`
- `frontend/src/components/landing/AnimatedTitle.tsx`
- `frontend/src/components/landing/LoginForm.tsx`
- `frontend/src/components/landing/HeroImage.tsx`

**Dependencias:** Ninguna

---

#### T5.5: Refactor Verify Land (anteriormente Audit)

**Estimación**: 3 días  
**Prioridad**: 🔴 Alta

**Descripción**: Transformar página de Auditoría en experiencia de verificación de terreno para público no técnico con enfoque de investigación ciudadana.

**Cambios principales de UX:**
- **Título**: "Auditoría" → **"Verificar terreno"**
- **CTA**: **"Verificá"** (en lugar de "Ejecutar auditoría")
- **Flujo**: Lugar → Mapa → Verificación (no coordenadas primero)
- **Input principal**: "Área de análisis" con opciones predefinidas:
  - Alrededores (500 m)
  - Zona (1 km)
  - Amplio (3 km)
  - Personalizado (en "Opciones Avanzadas")

**Nuevas features:**
- Búsqueda por dirección/localidad/parque nacional (no solo lat/lon)
- Checklist de verificación con 4 ítems guiados
- Microcopy estratégico para investigación:
  - "Algunos incendios son accidentales; otros pueden tener intereses detrás. Acá podés mirar evidencia y sacar tus conclusiones."
  - "Esto no demuestra intencionalidad por sí solo. Sirve para contrastar relatos con evidencia observable."
- Estados mejorados: vacío informativo, cargando con pasos, error accionable
- Layout 2 columnas: Mapa protagonista (60-70%) | Panel de control (30-40%)

**Componentes nuevos:**
- `LocationSearchInput` (autocomplete de lugares)
- `AnalysisAreaSelector` (chips con opciones predefinidas)
- `AdvancedOptionsAccordion` (lat/lon/ID catastral colapsable)
- `VerificationChecklistCard` (checklist de 4 ítems)
- `InvestigationHints` (microcopy guiado)
- `ResultsPanel` con estados (empty/loading/success/error)
- `EvidenceThumbnailsGrid` con gating de descarga

**Artefactos:**
- `frontend/src/pages/VerifyLand.tsx` (antes `Audit.tsx`)
- `frontend/src/components/verify/LocationSearchInput.tsx`
- `frontend/src/components/verify/AnalysisAreaSelector.tsx`
- `frontend/src/components/verify/AdvancedOptionsAccordion.tsx`
- `frontend/src/components/verify/VerificationChecklistCard.tsx`
- `frontend/src/components/verify/InvestigationHints.tsx`
- `frontend/src/components/verify/ResultsPanel.tsx`

**Backend:** Sin cambios (API `/api/v1/audit/land-use` mantiene contrato actual)

**Dependencias:** Ninguna

---

#### T5.6: Refactor Certificates (Exploración Visual)

**Estimación**: 3 días  
**Prioridad**: 🟡 Media

**Descripción**: Evolución de Certificates de enfoque legal a centro de exploración visual y descarga de evidencia satelital.

**Cambio de paradigma:**
- **De:** Certificado legal con firma digital
- **A:** Exploración visual con hasta 12 imágenes full HD seleccionables

**Flujo guiado de 4 pasos:**
1. **Selección del área:** Buscar lugar / marcar en mapa
2. **Selección de fechas/imágenes:**
   - Timeline con hitos ("pre-incendio", "post 3 meses", "post 1 año")
   - Máximo 12 imágenes
   - Feedback inmediato ("8 de 12 seleccionadas")
3. **Vista previa y resumen:**
   - Comparador before/after tipo slider
   - "Qué incluye el PDF" (lista)
   - Fuentes utilizadas (transparencia)
4. **Generación y descarga:**
   - PDF personalizable (historia antes/durante/después)
   - Indicadores: vegetación saludable, estrés hídrico, cicatriz

**Narrativa UX:**
- Traducir jerga técnica a conceptos humanos
- Tooltips con explicaciones ("¿qué estoy viendo?")
- Etiquetas con significado: "vegetación", "humedad", "cambios en el suelo"
- Confianza por transparencia (fuentes, limitaciones claras)

**Componentes nuevos:**
- `ImageSelectionGrid` (máx 12 imágenes con multi-select)
- `TemporalComparator` (slider before/after)
- `TimelineSelector` (navegación temporal con hitos)
- `PDFPreviewCard` (preview de contenido)
- `SourceTransparencyCard` (fuentes y limitaciones)

**Artefactos:**
- `frontend/src/pages/Certificates.tsx`
- `frontend/src/components/certificates/ImageSelectionGrid.tsx`
- `frontend/src/components/certificates/TemporalComparator.tsx`
- `frontend/src/components/certificates/TimelineSelector.tsx`
- `frontend/src/components/certificates/PDFPreviewCard.tsx`

**Dependencias:** T5.1, T5.2 (comparte componentes de comparación temporal)



---

### FASE 6: Testing & Observabilidad (0/4)

| Tarea | Descripción | Dependencias | Estimación |
|-------|-------------|--------------|------------|
| T6.1 | Tests unitarios (80% coverage) | Fases 1-5 | 2 días |
| T6.2 | Tests de integración | T6.1 | 2 días |
| T6.3 | Tests E2E (flujos críticos) | T6.2 | 2 días |
| T6.4 | Monitoreo y alertas | - | 1 día |

#### T6.1: Tests Unitarios

**Coverage target**: 80%

**Áreas clave**:
- `app/services/` (30 servicios)
- `app/utils/` (spatial, h3, validators)
- `app/core/security.py`
- `app/schemas/` (Pydantic validators)

**Framework**: pytest + pytest-asyncio + pytest-cov

**Comando**:
```bash
pytest tests/unit/ --cov=app --cov-report=term-missing --cov-fail-under=80
```

---

#### T6.2: Tests de Integración

**Áreas clave**:
- Endpoints de API (smoke tests)
- Workers Celery (con mocks de GEE/GCS)
- Database migrations (up/down)

**Framework**: pytest + httpx.AsyncClient

**Ejemplo**:
```python
async def test_land_use_audit_endpoint(client: AsyncClient):
    response = await client.post(
        "/api/v1/audit/land-use",
        json={"latitude": -31.4, "longitude": -64.18, "search_radius_meters": 5000},
        headers={"X-API-Key": "test-key"}
    )
    assert response.status_code == 200
    assert "is_violation" in response.json()
```

---

#### T6.3: Tests E2E

**Flujos críticos**:
1. **Login OAuth**: Google → Callback → Dashboard
2. **Auditoría legal**: Login → /audit → Submit → Results
3. **Exploración**: Login → /exploration → Wizard → PDF download
4. **Compra de créditos**: Login → /credits → MercadoPago → Callback

**Framework**: Cypress

**Ejemplo**:
```typescript
describe('Login Flow', () => {
  it('should login with Google OAuth', () => {
    cy.visit('/login')
    cy.get('[data-testid="login-google"]').click()
    cy.url().should('include', '/fires')
  })
})
```

---

#### T6.4: Monitoreo y Alertas

**Stack propuesto**: Grafana + Prometheus (free tier Oracle Cloud)

**Métricas a monitorear**:
- Latencia p50/p95/p99 por endpoint
- Error rate (4xx, 5xx)
- GEE quota usage
- Database size growth
- Worker queue length
- Active fires count

**Alertas**:
- API downtime > 5 min
- GEE quota > 80%
- Database size > 450MB
- Worker queue > 100 jobs

---

## 5. Timeline Estimado

### 5.1 Gantt Chart (Próximas 4 semanas)

```
Semana 1 (Feb 10-16):
├── T4.1 Security Hardening           [────────] 2 días
└── T4.2 Performance & Docs           [────────] 2 días

Semana 2 (Feb 17-23):
├── T4.3 Resilience & Cleanup         [──────────] 3 días
└── T5.1 Exploración Satelital        [────────] 4 días (inicia)

Semana 3 (Feb 24-Mar 2):
├── T5.1 (continúa)                   [─] 1 día
├── T5.2 Reportes Históricos          [──────────] 3 días
└── T5.3 PDF con hash y QR            [──────────] 3 días (inicia)

Semana 4 (Mar 3-9):
├── T5.3 (continúa)                   [──] 2 días
├── T6.1 Tests unitarios              [────────] 2 días
├── T6.2 Tests integración            [────────] 2 días
└── T6.3 Tests E2E                    [────────] 2 días (inicia)

Semana 5 (Mar 10-14):
├── T6.3 (continúa)                   [──] 1 día
└── T6.4 Monitoreo y alertas          [────] 1 día

═══════════════════════════════════════════════════════════
MVP COMPLETO: ~15 de Marzo 2026
```

---

## 6. Camino Crítico

```
Secuencia obligatoria:
T4.1 → T4.2 → T4.3 → T5.1 → T5.2 → T5.3 → T6.1 → T6.2 → T6.3 → MVP

Tareas paralelizables:
- T6.4 puede ejecutarse en paralelo con T6.1-T6.3
- T4.2 y T4.3 tienen subtareas independientes
```

**Dependencias bloqueantes**:
- T5.1 bloquea T5.2 y T5.3 (wizard base)
- T6.1 bloquea T6.2 y T6.3 (cobertura base)
- T4.1-T4.3 deben completarse antes de T5 (seguridad primero)

---

## 7. Riesgos y Mitigaciones

### 7.1 Riesgos Técnicos

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|-------------|---------|------------|
| Cuota GEE excedida | Media | Alto | Batch size configurable, priorización ponderada |
| Supabase 500MB límite | Baja | Medio | Archivado a Parquet tras 90 días |
| MercadoPago cambios API | Baja | Alto | Versionado de webhook handler, tests de integración |
| Latencia GEE > 120s | Alta | Medio | Timeout configurable, retry con backoff |
| Clustering ST-DBSCAN lento | Media | Bajo | Batch processing nocturno, índices espaciales |

### 7.2 Riesgos de Proyecto

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|-------------|---------|------------|
| Requerimientos cambian | Media | Medio | Documentación viva, validación iterativa |
| Deuda técnica acumulada | Alta | Medio | T4.3 dedicada a cleanup |
| Testing insuficiente | Media | Alto | 80% coverage obligatorio (T6.1) |

---

## 8. Métricas de Éxito

### 8.1 Métricas Técnicas

| Métrica | Target | Actual | Estado |
|---------|--------|--------|--------|
| Cobertura de tests | 80% | ~45% | 🟡 |
| Latencia p95 (dashboard) | < 2s | ~1.5s | ✅ |
| Latencia p95 (audit) | < 3s | ~2.3s | ✅ |
| GEE quota usage | < 80% | ~45% | ✅ |
| Database size | < 450MB | ~280MB | ✅ |
| API uptime | > 99.5% | ~99.8% | ✅ |

### 8.2 Métricas de Negocio (Post-MVP)

| Métrica | Target 3 meses | Medición |
|---------|----------------|----------|
| Usuarios registrados | 100 | Google Analytics |
| Consultas de auditoría | 500 | `land_use_audits` count |
| Reportes generados | 50 | `exploration_investigations` count |
| Certificados emitidos | 20 | `certificates` count |
| Free tier compliance | 100% | Monitoreo cuotas |

---

## 9. Post-MVP Roadmap

### Fase 7: Features Avanzados (Futuro)

| Feature | Descripción | Prioridad |
|---------|-------------|-----------|
| **UC-F12: VAE Monitoring** | Monitoreo de vegetación post-incendio | 🟡 Media |
| **Geocerca personalizada** | Alertas push para áreas de interés | 🟢 Baja |
| **Export a Parquet** | Para análisis BigQuery | 🟢 Baja |
| **API pública documentada** | OpenAPI 3.0 + Swagger UI | 🟡 Media |
| **Multi-tenant** | Soporte para instituciones | 🔴 Alta |
| **Mobile App** | React Native para alertas | 🟢 Baja |

### Fase 8: Escalabilidad (6-12 meses)

- Migración a PostgreSQL managed (si > 500MB)
- CDN para thumbnails (Cloudflare R2)
- Horizontal scaling de workers
- Kubernetes deployment opcional

---

## 10. Referencias y Recursos

### 10.1 Documentación del Proyecto

| Documento | Ubicación | Propósito |
|-----------|-----------|-----------|
| Sistema Overview | `docs/v2/1-arquitectura/sistema_overview.md` | Arquitectura completa |
| Data Model (DER) | `docs/v2/2-der/modelo_datos_completo.md` | Esquema de BD v2.0 |
| Backend API | `docs/v2/3-backend/api_documentation.md` | Endpoints y servicios |
| Frontend | `docs/v2/4-frontend/frontend_documentation.md` | React 18 + Vite |

### 10.2 Arquitectura Original

| Documento | Ubicación | Estado |
|-----------|-----------|--------|
| Casos de Uso | `docs/architecture/final/2_casos_de_uso_final.md` | ✅ Implementado |
| Roadmap Técnico | `docs/architecture/final/3_technical_roadmap.md` | 📝 Este documento actualiza |
| Decisiones Validadas | `docs/architecture/final/5_preguntas_roadmap_final.md` | ✅ Referencia |

### 10.3 Herramientas de Desarrollo

| Herramienta | Uso | Link |
|-------------|-----|------|
| FastAPI Docs | API testing | `http://localhost:8000/docs` |
| Supabase Dashboard | Database management | `https://<project>.supabase.co` |
| Celery Flower | Worker monitoring | `http://localhost:5555` |
| Vite Dev Server | Frontend preview | `http://localhost:5173` |

---

## 11. Próximos Pasos Inmediatos

### Semana actual (Feb 10-16, 2026)

**Prioridad 1**: Iniciar T4.1 (Security Hardening)
- [ ] Implementar hard caps en page_size/max_records
- [ ] Configurar CORS estricto por ambiente
- [ ] Añadir PII scrubber a logging

**Prioridad 2**: Ejecutar T4.2 (Performance & Docs)
- [ ] Verificar índices GIST
- [ ] Configurar refresh MV diario
- [ ] Docstrings en servicios core

**Prioridad 3**: Planificar T5.1 (Exploración Satelital)
- [ ] Diseñar wizard UI flow (Figma/wireframes)
- [ ] Definir schema de `exploration_investigations`
- [ ] Estimar costos GEE por reporte

---

**Documento actualizado**: Febrero 2026  
**Próxima revisión**: Post T4.3 (Refactoring completo)  
**Mantenedor**: Lead Developer  
**Estado**: 🟢 En progreso activo
