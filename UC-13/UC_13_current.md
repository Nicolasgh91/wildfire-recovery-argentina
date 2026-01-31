

## UC-13: Fire Grid Visualization and Filtering

### 📋 Descripción
Página de grilla/lista para consultar incendios registrados con filtros por provincia, área protegida, fechas y estado.

### 🏗️ Análisis de Infraestructura Existente

#### A. Base de Datos ✅

```sql
-- Tabla fire_events YA EXISTE con campos requeridos:
-- ✅ id, start_date, end_date, province, department
-- ✅ avg_confidence, total_detections, avg_frp, max_frp
-- ✅ is_significant, has_satellite_imagery
-- ✅ Índices GIST para location
-- ✅ Índices para date, province, is_significant

-- Tabla fire_detections YA EXISTE:
-- ✅ satellite, confidence_normalized, acquisition_date
-- ✅ fire_event_id (FK)
```

**Estado:** ✅ Tablas existen y están indexadas

#### B. Backend (Endpoints)

| Endpoint | Requerido | Estado | Gap |
|----------|-----------|--------|-----|
| `GET /fires` | Paginado con filtros | ✅ Existe | Faltan algunos filtros |
| `GET /fires/{id}` | Detalle completo | ✅ Existe | OK |
| `GET /fires/export` | CSV/XLSX | ❌ No existe | Implementar |

**Estado:** ⚠️ Parcialmente implementado (80%)

#### C. Frontend

| Componente | Requerido | Estado |
|------------|-----------|--------|
| Tabla/Grid | DataGrid con paginación | ❌ No existe |
| Filtros | Sidebar/Modal de filtros | ❌ No existe |
| Mapa integrado | Vista mapa opcional | ❌ No existe |

**Estado:** ❌ Frontend no implementado

### 📊 Gap Analysis Detallado

#### Backend - Filtros Faltantes

```python
# Filtros actuales en GET /fires (existentes):
# ✅ page, page_size
# ✅ province
# ✅ from_date, to_date

# Filtros requeridos por UC-13 (faltantes):
# ❌ protected_area_id
# ❌ status (active, controlled, extinguished)
# ❌ min_confidence
# ❌ is_significant
# ❌ sort_by, sort_order
# ❌ bbox (filtro espacial)
```

#### Endpoint Export (Nuevo)

```python
# Requerido:
GET /api/v1/fires/export?format=csv&...filtros...
GET /api/v1/fires/export?format=xlsx&...filtros...
```

### 📊 Estimación de Esfuerzo

| Componente | Horas | Prioridad |
|------------|-------|-----------|
| Agregar filtros faltantes a GET /fires | 3h | Alta |
| Endpoint GET /fires/export (CSV) | 2h | Media |
| Endpoint GET /fires/export (XLSX) | 2h | Baja |
| Frontend: Componente DataGrid | 4h | Media |
| Frontend: Panel de filtros | 3h | Media |
| Frontend: Integración con mapa | 4h | Baja |
| Tests | 2h | Alta |
| **TOTAL** | **20h** | - |

**Solo Backend:** 7h
**Con Frontend básico:** 14h
**Completo con mapa:** 20h

### 🎯 Viabilidad

| Criterio | Evaluación |
|----------|------------|
| Técnica | ✅ Muy alta (infraestructura existe) |
| Recursos | ✅ Bajo (7-20h) |
| Costo | ✅ $0 |
| Alineación MVP | ✅ Alta (consulta de datos core) |
| Valor agregado | ✅ Alto (usabilidad) |
| Urgencia | 🟡 Media |

### 📌 Recomendación UC-13

```
DECISIÓN: IMPLEMENTAR EN 2 FASES

Fase A (Inmediata - 7h):
1. Agregar filtros faltantes a GET /fires
2. Agregar endpoint GET /fires/export (CSV)
3. Tests

Fase B (Con Frontend - 13h adicionales):
1. Componente DataGrid React
2. Panel de filtros
3. Vista de mapa integrada (opcional)
```

---

## 📊 Matriz de Decisión Final

| UC | Viabilidad Técnica | Esfuerzo | Alineación MVP | Decisión |
|----|-------------------|----------|----------------|----------|
| UC-12 | ✅ Alta | 🔴 57h | ⚠️ Baja | **POSTERGAR** |
| UC-13 | ✅ Muy Alta | 🟢 7-20h | ✅ Alta | **IMPLEMENTAR** |

---

## 🗺️ Plan de Implementación Propuesto

### Semana Actual: UC-13 Backend

```
DÍA 1 (4h):
├── ✅ Revisar endpoint GET /fires actual
├── 🔜 Agregar filtros: protected_area_id, min_confidence, is_significant
├── 🔜 Agregar filtros: status, sort_by, sort_order
└── 🔜 Agregar filtro espacial: bbox

DÍA 2 (3h):
├── 🔜 Endpoint GET /fires/export (CSV)
├── 🔜 Tests unitarios
└── 🔜 Documentación OpenAPI
```

### Próxima Semana: UC-13 Frontend (Opcional)

```
├── 🔜 Componente FiresDataGrid
├── 🔜 Panel de filtros
├── 🔜 Integración con página existente
└── 🔜 Tests E2E
```

### Post-MVP: UC-12

```
├── 🔜 Schema SQL para shelters/visitor_logs
├── 🔜 Backend CRUD básico
├── 🔜 PWA offline-first
└── 🔜 Sincronización
```

---

## 📁 Archivos a Modificar/Crear para UC-13

```
# Backend (modificar)
app/api/routes/fires.py          # Agregar filtros
app/schemas/fire.py              # Agregar query params

# Backend (crear)
app/api/routes/export.py         # Endpoint export
app/services/export_service.py   # Lógica CSV/XLSX

# Tests
tests/test_fires_filters.py      # Tests de filtros
tests/test_export.py             # Tests de export

# Frontend (crear - opcional)
frontend/src/pages/FiresGrid.tsx
frontend/src/components/FiresDataGrid.tsx
frontend/src/components/FiresFilters.tsx
```

---

## ✅ Conclusiones

1. **UC-11 (Historical Reports):** ✅ Ya implementado correctamente (era lo que llamamos "UC-12" en la conversación)

2. **UC-12 (Visitor Registration):** ⚠️ Postergar a Phase 3
   - No es core del producto
   - Requiere PWA offline completo
   - Schema no existe
   - ~60h de desarrollo

3. **UC-13 (Fire Grid):** ✅ Implementar ahora
   - Infraestructura existe
   - Solo faltan filtros adicionales
   - ~7h backend, ~13h frontend
   - Alta alineación con MVP

**Próximo paso recomendado:** Implementar filtros faltantes de UC-13 en `GET /fires`.