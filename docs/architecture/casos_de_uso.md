# 📋 ForestGuard API - Casos de uso completos

## Resumen ejecutivo

Este documento detalla los **13 casos de uso principales** que la API ForestGuard está diseñada para resolver. Cada caso de uso está vinculado a necesidades reales de fiscalización ambiental, transparencia institucional y defensa del patrimonio natural de Argentina bajo el marco de la Ley 26.815 (Manejo del Fuego).

---

## 🔴 Categoría: Fiscalización y aplicación de la ley

### UC-01: Auditoría de cambio de uso del suelo post-incendio

**Descripción:**  
Determinar si una parcela específica fue afectada por un incendio y si existe prohibición legal para cambiar su uso del suelo (loteo, agricultura, construcción).

**Actor principal:** Escribanos, inspectores municipales, compradores de terrenos

**Flujo principal:**
1. Usuario ingresa coordenadas geográficas o ID catastral
2. Sistema busca eventos de incendio en un radio de 500m (configurable)
3. Sistema determina si la parcela intersecta con área protegida
4. Sistema calcula fecha de prohibición según Ley 26.815 Art. 22 bis:
   - 60 años para bosques nativos y áreas protegidas
   - 30 años para zonas agrícolas/praderas
5. Sistema retorna:
   - Lista de incendios históricos
   - Fechas de prohibición
   - Imágenes satelitales pre/post fuego
   - Status legal actual

**Datos requeridos:**
- `fire_events` (eventos de incendio)
- `protected_areas` (áreas protegidas)
- `fire_protected_area_intersections` (cruces espaciales)
- `satellite_images` (evidencia visual)

**Endpoint:**
```
GET /api/v1/audit/land-use?lat={lat}&lon={lon}&radius={meters}
```

**Respuesta ejemplo:**
```json
{
  "location": {"lat": -27.4658, "lon": -58.8346},
  "fires_found": 2,
  "earliest_fire_date": "2015-08-22",
  "prohibition_until": "2075-08-22",
  "is_prohibited": true,
  "protected_area": {
    "name": "Parque Nacional Chaco",
    "category": "national_park"
  },
  "evidence": [
    {
      "fire_id": "uuid-123",
      "date": "2015-08-22",
      "image_url": "https://r2.forestguard.ar/fires/uuid-123/post_fire.jpg"
    }
  ]
}
```

**Criterios de éxito:**
- ✅ Precisión espacial < 500m
- ✅ Respuesta en < 2 segundos
- ✅ Incluye evidencia visual verificable

---

### UC-02: Generación de peritaje judicial forense

**Descripción:**  
Producir un informe técnico con contexto climático, cronología del evento y evidencia satelital para uso en procesos judiciales.

**Actor principal:** Peritos judiciales, fiscales ambientales, abogados

**Flujo principal:**
1. Usuario solicita peritaje para un incendio específico (ID o coordenadas)
2. Sistema recopila:
   - Datos de detecciones satelitales (VIIRS/MODIS)
   - Condiciones climáticas del día del evento (temperatura, viento, sequía)
   - Imágenes satelitales antes/después
   - Historial de incendios en la zona (recurrencia)
3. Sistema genera PDF estructurado con:
   - Cronología del evento
   - Mapa de propagación
   - Análisis de condiciones propicias
   - Sección de "Hallazgos Clave"
4. PDF incluye hash SHA256 para verificación de integridad

**Datos requeridos:**
- `fire_detections` (detecciones individuales)
- `fire_events` (evento agregado)
- `climate_data` (contexto meteorológico)
- `satellite_images` (evidencia visual)
- `data_source_metadata` (transparencia de fuentes)

**Endpoint:**
```
POST /api/v1/reports/judicial
Content-Type: application/json

{
  "fire_event_id": "uuid-456",
  "report_type": "full_forensic",
  "language": "es"
}
```

**Respuesta:**
```json
{
  "report_id": "FG-REPORT-2025-001",
  "pdf_url": "https://r2.forestguard.ar/reports/FG-REPORT-2025-001.pdf",
  "verification_hash": "a3f5b8c9d2e1...",
  "generated_at": "2025-01-24T14:30:00Z",
  "valid_until": "2026-01-24T14:30:00Z"
}
```

**Criterios de éxito:**
- ✅ Incluye disclaimers sobre limitaciones de datos
- ✅ Cita fuentes con precisión (NASA FIRMS, ERA5, Sentinel-2)
- ✅ Formato admisible en tribunales

---

### UC-07: Certificación de condición legal del terreno

**Descripción:**  
Emitir un certificado digital verificable que indique si un terreno es legalmente explotable o tiene restricciones por incendios previos.

**Actor principal:** Inmobiliarias, escribanos, compradores, bancos (para hipotecas)

**Flujo principal:**
1. Usuario solicita certificado para coordenadas específicas
2. Sistema ejecuta auditoría completa (UC-01)
3. Sistema genera certificado con:
   - Número único de certificado
   - QR code para verificación online
   - Status legal claro: `clear`, `prohibited`, `restricted`
   - Vigencia del certificado (ej: 90 días)
   - Hash SHA256 del contenido
4. Certificado se guarda en `land_certificates` para auditoría

**Datos requeridos:**
- `land_use_audits` (log de la consulta)
- `fire_events`, `protected_areas` (análisis)
- `land_certificates` (registro del certificado)

**Endpoint:**
```
POST /api/v1/certificates/request
Content-Type: application/json

{
  "latitude": -34.6037,
  "longitude": -58.3816,
  "cadastral_id": "BA-123-456-789",
  "requester_email": "escribano@example.com"
}
```

**Respuesta:**
```json
{
  "certificate_number": "FG-CERT-2025-001234",
  "legal_status": "prohibited_recent_fire",
  "is_legally_exploitable": false,
  "prohibition_expires_on": "2054-03-15",
  "pdf_url": "https://forestguard.ar/certificates/FG-CERT-2025-001234.pdf",
  "qr_code_url": "https://forestguard.ar/verify/FG-CERT-2025-001234",
  "verification_hash": "b7e4f3a2...",
  "issued_at": "2025-01-24T15:00:00Z",
  "valid_until": "2025-04-24T15:00:00Z"
}
```

**Criterios de éxito:**
- ✅ Certificado verificable públicamente
- ✅ Hash anti-falsificación
- ✅ Lenguaje claro y no técnico
- ✅ Aceptado por instituciones financieras

---

## 🟡 Categoría: Detección y alertas

### UC-03: Análisis de recurrencia y patrones

**Descripción:**  
Identificar zonas con incendios recurrentes para detectar patrones sospechosos de cambio de uso del suelo sistemático.

**Actor principal:** ONGs ambientales, fiscalías especializadas, investigadores

**Flujo principal:**
1. Usuario define área de interés (polígono o radio)
2. Sistema busca todos los incendios en los últimos N años
3. Sistema calcula:
   - Densidad de incendios por km²
   - Temporalidad (estacional vs fuera de temporada)
   - Superposiciones (fuegos en la misma área)
4. Sistema clasifica zonas como:
   - `low_risk`: < 1 incendio cada 5 años
   - `medium_risk`: 1-3 incendios cada 5 años
   - `high_risk`: > 3 incendios cada 5 años (sospechoso)
5. Genera mapa de calor (heatmap) de recurrencia

**Datos requeridos:**
- `fire_events` (histórico completo)
- `fire_detections` (para análisis temporal fino)

**Endpoint:**
```
GET /api/v1/analysis/recurrence?bbox={minLon},{minLat},{maxLon},{maxLat}&years=10
```

**Criterios de éxito:**
- ✅ Identifica zonas con > 3 incendios/5 años
- ✅ Visualización clara de patrones
- ✅ Exportable como GeoJSON para SIG

---

### UC-04: Alerta temprana por capacidad de carga en áreas protegidas

**Descripción:**  
Correlacionar afluencia de visitantes en parques con riesgo de incendio para emitir alertas preventivas.

**Actor principal:** APN (Administración de Parques Nacionales), guardaparques

**Flujo principal:**
1. Sistema recibe datos de visitantes (tickets vendidos, estimaciones)
2. Sistema calcula capacidad de carga vs ocupación real
3. Sistema cruza con:
   - Historial de incendios en la misma temporada
   - Condiciones climáticas actuales (sequía, viento)
4. Si capacidad > 80% + condiciones de alto riesgo → Alerta
5. Notificación a guardaparques para reforzar vigilancia

**Datos requeridos:**
- `protected_areas` (parques)
- `fire_events` (historial)
- `climate_data` (condiciones actuales)
- Datos externos: afluencia de visitantes (API de APN o manual)

**Endpoint:**
```
POST /api/v1/alerts/park-capacity
Content-Type: application/json

{
  "park_id": "uuid-park-nahuel-huapi",
  "visitor_count": 1500,
  "date": "2025-01-15"
}
```

**Criterios de éxito:**
- ✅ Alerta emitida con > 12 horas de anticipación
- ✅ Tasa de falsos positivos < 20%

---

### UC-08: Detección de cambio de uso post-incendio

**Descripción:**  
Monitorear automáticamente áreas quemadas para detectar actividad humana (construcción, agricultura, minería) que viole la prohibición legal.

**Actor principal:** Fiscales ambientales, ONGs, ciudadanos vigilantes

**Flujo principal:**
1. Sistema (VAE Service) procesa imágenes mensuales de áreas quemadas
2. Calcula NDVI y detecta anomalías:
   - Caída drástica de NDVI sin recuperación → `bare_soil`
   - Patrones geométricos → `construction_detected`, `roads_detected`
   - Vegetación en cuadrícula → `agriculture_detected`
3. Si detección positiva → Crea registro en `land_use_changes`
4. Sistema notifica a revisores humanos
5. Si se confirma → Genera alerta a autoridades

**Datos requeridos:**
- `fire_events` (eventos base)
- `vegetation_monitoring` (NDVI mensual)
- `satellite_images` (pre/post comparación)
- `land_use_changes` (detecciones)

**Endpoint (Worker automático):**
```
POST /api/v1/workers/detect-land-use-change
Content-Type: application/json

{
  "fire_event_id": "uuid-789",
  "monitoring_month": 6
}
```

**Respuesta:**
```json
{
  "change_detected": true,
  "change_type": "construction_detected",
  "confidence": 0.85,
  "affected_area_hectares": 12.5,
  "before_image": "https://r2.forestguard.ar/...",
  "after_image": "https://r2.forestguard.ar/...",
  "is_potential_violation": true
}
```

**Criterios de éxito:**
- ✅ Detección automática > 75% de casos reales
- ✅ Falsos positivos < 30%
- ✅ Alerta generada en < 48 horas desde adquisición de imagen

---

## 🟢 Categoría: Análisis y reportes

### UC-05: Tendencias históricas y proyecciones

**Descripción:**  
Analizar patrones temporales de incendios para identificar tendencias de largo plazo y zonas de riesgo emergente.

**Actor principal:** Investigadores, planificadores territoriales, medios de comunicación

**Flujo principal:**
1. Usuario selecciona rango temporal (ej: 2004-2024)
2. Usuario define filtros:
   - Provincia/región
   - Tipo de área (protegida, agrícola, urbana)
   - Temporada (invierno, verano)
3. Sistema calcula:
   - Número de incendios por año
   - Hectáreas afectadas totales
   - Intensidad promedio (FRP)
   - Distribución espacial (migración de zonas calientes)
4. Sistema genera:
   - Gráficos de serie temporal
   - Mapas de evolución espacial
   - Predicción básica de tendencia (regresión lineal)

**Datos requeridos:**
- `fire_events` (histórico completo 2004-2024)
- `protected_areas` (clasificación de zonas)

**Endpoint:**
```
GET /api/v1/analysis/trends?start_year=2004&end_year=2024&province=Corrientes
```

**Criterios de éxito:**
- ✅ Visualización interactiva
- ✅ Exportable como CSV/JSON
- ✅ Incluye intervalos de confianza en proyecciones

---

### UC-06: Seguimiento de recuperación de vegetación (reforestación)

**Descripción:**  
Monitorear la recuperación natural de áreas quemadas mediante índices de vegetación (NDVI) durante 36 meses post-incendio.

**Actor principal:** Ecólogos, ONGs de reforestación, APN

**Flujo principal:**
1. Sistema identifica áreas quemadas
2. Sistema (VAE Service) procesa mensualmente imagen Sentinel-2
3. Calcula NDVI promedio del área quemada
4. Compara con NDVI pre-fuego (baseline) detectando tasa de recuperación
5. Calcula % de recuperación
6. Almacena en `vegetation_monitoring`
7. Genera gráfico de evolución temporal

**Datos requeridos:**
- `fire_events` (área base)
- `satellite_images` (imágenes mensuales)
- `vegetation_monitoring` (serie temporal de NDVI)

**Endpoint:**
```
GET /api/v1/monitoring/recovery/{fire_event_id}
```

**Respuesta:**
```json
{
  "fire_event_id": "uuid-456",
  "fire_date": "2023-08-15",
  "baseline_ndvi": 0.65,
  "monitoring_data": [
    {"month": 1, "date": "2023-09-15", "ndvi": 0.22, "recovery": 34},
    {"month": 6, "date": "2024-02-15", "ndvi": 0.48, "recovery": 74},
    {"month": 12, "date": "2024-08-15", "ndvi": 0.61, "recovery": 94}
  ]
}
```

**Criterios de éxito:**
- ✅ Imágenes sin nubes > 80% de los meses
- ✅ Detección de "no recuperación" (posible uso ilegal)

---

### UC-10: Evaluación de confiabilidad del dato

**Descripción:**  
Proveer métricas de calidad y confiabilidad de cada evento de incendio para uso en peritajes y análisis científicos.

**Actor principal:** Peritos, investigadores, periodistas de datos

**Flujo principal:**
1. Usuario consulta evento específico o conjunto de eventos
2. Sistema calcula "Reliability Score" (0-100) basado en:
   - Confianza promedio de detecciones (40%)
   - Disponibilidad de imágenes satelitales (20%)
   - Datos climáticos disponibles (20%)
   - Número de detecciones independientes (20%)
3. Sistema clasifica como: `high`, `medium`, `low` reliability
4. Sistema expone metadata de fuentes:
   - Resolución espacial (VIIRS 375m, Sentinel-2 10m)
   - Limitaciones conocidas
   - Admisibilidad legal

**Datos requeridos:**
- `fire_event_quality_metrics` (vista)
- `data_source_metadata` (tabla de fuentes)

**Endpoint:**
```
GET /api/v1/quality/fire-event/{fire_event_id}
```

**Respuesta:**
```json
{
  "fire_event_id": "uuid-789",
  "reliability_score": 87,
  "reliability_class": "high",
  "metrics": {
    "satellite_sources": 2,
    "avg_confidence": 92,
    "total_detections": 5,
    "has_imagery": true,
    "has_climate_data": true
  },
  "data_sources": [
    {
      "name": "NASA_FIRMS_VIIRS",
      "resolution": "375m",
      "accuracy": "85%",
      "admissible_in_court": true
    }
  ],
  "limitations": [
    "Small fires < 14 hectares may not be detected",
    "Cloud cover may prevent optical imagery acquisition"
  ]
}
```

**Criterios de éxito:**
- ✅ Transparencia total de fuentes
- ✅ Score reproducible y documentado
- ✅ Útil para defensa legal

---

### UC-11: Búsqueda y generación de reportes históricos en áreas protegidas

**Descripción:**  
Implementar funcionalidad que permita la identificación, validación y monitoreo de eventos de incendio históricos en áreas protegidas, con la capacidad de generar reportes detallados en formato PDF.

**Actor principal:** Guardaparques, Investigadores, Autoridades de aplicación

**Flujo principal:**
1. Usuario configura búsqueda de imágenes de incendio por periodo de tiempo.
2. Usuario selecciona un área protegida específica.
3. Sistema muestra la cantidad de áreas afectadas por los eventos identificados.
4. Usuario solicita generación de reporte PDF.
5. Sistema obtiene imágenes Pre-Fuego (baja nubosidad, ventana 30 días previos).
6. Sistema obtiene imágenes Post-Fuego (frecuencia configurable diaria/mensual/anual, hasta 1 año post-fuego, máx 12 imágenes).
7. Sistema (ERS) genera PDF incluyendo:
   - Grilla de imágenes
   - Metadatos, hash y código QR de verificación
   - Logo del proyecto y branding oficial

**Datos requeridos:**
- `protected_areas`
- `sentinel_2_imagery` (vía STAC Copernicus/Planetary Computer)
- `fire_events_metadata`

**Requerimientos técnicos:**
- **Calidad de Imagen**: Resolución suficiente para identificar construcciones, caminos, vegetación (Sentinel-2 viable).
- **Eficiencia**: Queries optimizadas (lightweight) y caching con TTL (Redis).
- **Almacenamiento**: No guardar imágenes/reportes pesados en BD, solo metadatos.

**Endpoint:**
```
POST /api/v1/reports/historical-fire
Content-Type: application/json

{
  "protected_area_id": "uuid-park-123",
  "date_range": {"start": "2023-01-01", "end": "2023-12-31"},
  "report_config": {
    "post_fire_frequency": "monthly",
    "max_images": 12
  }
}
```

**Criterios de éxito:**
- ✅ Identificación clara de elementos en terreno
- ✅ Reporte PDF generado con branding correcto
- ✅ Uso eficiente de API STAC (imágenes recortadas al AOI)

---

### UC-13: Visualización y filtrado de grilla de incendios

**Descripción:**  
Construir una página de grilla/lista para consultar incendios registrados y filtrar por atributos clave, soportando consultas típicas (por provincia, área protegida, fechas y estado).

**Actor principal:** Usuarios generales, analistas, operadores

**Flujo principal:**
1. Usuario accede a la sección "Incendios"
2. Visualiza grilla paginada con columnas clave:
   - ID de evento / ID de detección
   - Última detección / Fecha de inicio
   - Provincia
   - Área protegida (sí/no + nombre)
   - Estado/Categoría
   - Confianza (normalizada)
   - Severidad (FRP total, detecciones, área estimada)
3. Aplica filtros:
   - Provincia
   - Categoría/Estado (ej: Sospechado/Confirmado/Controlado)
   - Área Protegida
   - Rango de fechas
   - "Solo incendios actuales"
4. Ordena por fecha/severidad
5. Abre detalle del incendio (opcional) para ver línea de tiempo/mapa

**Reglas de negocio:**
- RB-01: La grilla debe paginar desde la BD (no cargar todo en memoria)
- RB-02: Los filtros deben traducirse a consultas eficientes (índices)
- RB-03: "Incendios actuales" definido por ventana de tiempo (ej: detección en últimos N días) o campo `is_active`

**Datos requeridos:**
- `fire_events` (eventos consolidados)
- `fire_detections` (detecciones agregadas)

**Endpoint:**
```
GET /api/v1/fires?province[]={province}&protected_area_id={id}&from={date}&to={date}&status={status}&active={bool}&min_confidence={float}&page={n}&page_size={n}&sort={field}
GET /api/v1/fires/{id}
GET /api/v1/fires/export?... (opcional CSV/XLSX)
```

**Criterios de éxito:**
- ✅ Rendimiento: respuesta < 1-2s con paginación
- ✅ Observabilidad: logs para consultas lentas
- ✅ Seguridad: proteger filtros administrativos por rol

---

### UC-12: Registro digital de visitantes para refugios de montaña (Offline-first)

**Descripción:**  
Digitalizar el registro diario de visitantes (entradas y pernoctes) en refugios de montaña, reemplazando registros en papel con un sistema **mobile-first**, **offline-first**, seguro y auditable con sincronización automática y generación de estadísticas/exportación.

**Actor principal:** Operadores de refugio, administradores de APN, auditores

**Flujo principal:**
1. Operador abre la app (web/PWA)
2. Selecciona "Nuevo Registro"
3. Completa:
   - Refugio
   - Fecha (default: hoy)
   - Tipo de registro: Entrada de día / Pernocte
4. Completa datos del **líder del grupo**
5. Agrega acompañantes vía **lista dinámica**:
   - Nombre completo
   - Edad o rango de edad
   - Documento (opcional)
6. Sistema calcula automáticamente el total de personas
7. Guarda el registro:
   - Si online → sincroniza con backend
   - Si offline → guardado local (IndexedDB)
8. Cuando se restablece la conectividad, el sistema sincroniza automáticamente
9. Operador puede editar el registro **hasta 30 minutos** después de la primera sincronización
10. Administrador puede consultar estadísticas y exportar datos

**Reglas de negocio:**
- RB-01 (Offline-first): El sistema debe permitir crear y almacenar registros sin conexión
- RB-02 (Sincronización): Los registros locales se sincronizan automáticamente cuando hay conectividad
- RB-03 (Edición limitada): Un registro solo puede editarse hasta **30 minutos** después de `first_submitted_at`
- RB-04 (Auditoría): Cada edición genera una revisión histórica
- RB-05 (Seguridad): Acceso restringido por roles (RLS / JWT)
- RB-06 (Exportación): Los datos pueden exportarse en CSV o XLSX

**Datos requeridos:**
- `shelters` (catálogo de refugios)
- `visitor_logs` (registros de visitas)
- `visitor_log_companions` (detalles de acompañantes)
- `visitor_log_revisions` (historial de ediciones)

**Endpoints:**
```
POST /api/v1/visitor-logs
PATCH /api/v1/visitor-logs/{id} (valida ventana de 30 min)
GET /api/v1/visitor-logs?shelter_id=&from=&to=
GET /api/v1/visitor-logs/export?from=&to=&province=&shelter_id= (CSV/XLSX)
GET /api/v1/shelters?province=&q=
```

**Stack Frontend (Offline-first):**
- Vite + React + TypeScript
- Tailwind CSS (branding)
- TanStack Query (cache persistence + offline mutation queue)
- IndexedDB / LocalForage
- PWA (Service Worker, asset caching, instalable)

**Criterios de éxito:**
- ✅ Elimina registros en papel
- ✅ Mejora trazabilidad y calidad de datos
- ✅ Habilita análisis estadístico histórico
- ✅ Base para correlación con riesgo ambiental y emergencias

---

## 🔵 Categoría: Participación ciudadana

### UC-09: Soporte a denuncias ciudadanas

**Descripción:**  
Permitir que ciudadanos, ONGs y comunidades reporten actividad sospechosa en áreas quemadas y reciban un paquete de evidencia satelital automático.

**Actor principal:** Ciudadanos, ONGs, comunidades indígenas, medios

**Flujo principal:**
1. Usuario accede a formulario web (anónimo o con registro)
2. Usuario marca ubicación en mapa y describe:
   - Tipo de actividad (construcción, desmonte, etc)
   - Fecha observada
   - Fotos opcionales (subidas a R2)
3. Sistema automáticamente:
   - Busca incendios históricos en 1km de radio
   - Busca áreas protegidas cercanas
   - Genera paquete de evidencia usando Evidence Reporting Service (ERS):
     - Imágenes satelitales pre/post fuego
     - Cronología de incendios
     - Status legal del área
4. Denuncia queda registrada en `citizen_reports`
5. Sistema notifica a revisores (ONGs, autoridades)
6. Si se verifica → Se marca como `forwarded_to_authorities`

**Datos requeridos:**
- `citizen_reports` (denuncias)
- `fire_events`, `protected_areas` (cruce automático)
- `satellite_images` (evidencia)

**Endpoint:**
```
POST /api/v1/reports/citizen/submit
Content-Type: application/json

{
  "latitude": -27.1234,
  "longitude": -55.4567,
  "report_type": "construction_in_prohibited_area",
  "description": "Se observan movimientos de suelo y maquinaria en zona quemada en 2022",
  "observed_date": "2025-01-20",
  "reporter_email": "ciudadano@example.com",
  "is_anonymous": false
}
```

**Respuesta:**
```json
{
  "report_id": "uuid-report-123",
  "status": "submitted",
  "evidence_package_url": "https://r2.forestguard.ar/reports/uuid-report-123/evidence.zip",
  "related_fires": 2,
  "related_protected_areas": ["Parque Provincial XYZ"],
  "created_at": "2025-01-24T16:00:00Z"
}
```

**Criterios de éxito:**
- ✅ Formulario simple (< 5 minutos completar)
- ✅ Evidencia generada automáticamente en < 1 minuto
- ✅ Opción de anonimato respetada
- ✅ Integración con canal de Telegram/WhatsApp para ONGs

---

## 📊 Matriz de casos de uso

| UC | Nombre | Prioridad | Complejidad | Impacto Legal | Impacto Social |
|----|--------|-----------|-------------|---------------|----------------|
| UC-01 | Auditoría Anti-Loteo | 🔴 ALTA | Media | ⚖️ Alto | 🏘️ Alto |
| UC-02 | Peritaje Judicial | 🔴 ALTA | Alta | ⚖️ Muy Alto | 📜 Medio |
| UC-03 | Recurrencia | 🟡 MEDIA | Media | ⚖️ Medio | 🔍 Alto |
| UC-04 | Alerta Temprana | 🟡 MEDIA | Baja | ⚖️ Bajo | 🚨 Medio |
| UC-05 | Tendencias | 🟢 BAJA | Media | ⚖️ Bajo | 📊 Alto |
| UC-06 | Reforestación | 🟡 MEDIA | Alta | ⚖️ Medio | 🌳 Alto |
| UC-07 | Certificación | 🔴 ALTA | Media | ⚖️ Muy Alto | 💼 Alto |
| UC-08 | Cambio de Uso | 🔴 ALTA | Muy Alta | ⚖️ Alto | 🚧 Alto |
| UC-09 | Denuncias | 🟡 MEDIA | Baja | ⚖️ Medio | 🧑‍🤝‍🧑 Muy Alto |
| UC-10 | Calidad Dato | 🔴 ALTA | Baja | ⚖️ Alto | 🔬 Medio |
| UC-11 | Reportes Hist. | 🟡 MEDIA | Media | ⚖️ Medio | 📊 Alto |
| UC-12 | Registro Visitantes | 🟡 MEDIA | Media | ⚖️ Bajo | 🏔️ Alto |
| UC-13 | Grilla Incendios | 🟢 BAJA | Baja | ⚖️ Bajo | 📋 Medio |

---

## 🎯 Roadmap de implementación

### Fase 1: MVP core (semanas 1-6)
- ✅ UC-01: Auditoría Anti-Loteo
- ✅ UC-02: Peritaje Judicial
- ✅ UC-06: Reforestación (básico)
- ✅ UC-10: Calidad del Dato
- ✅ UC-11: Reportes Históricos (MVP)

### Fase 2: Certificación y alertas (semanas 7-8)
- ✅ UC-07: Certificación Legal
- ✅ UC-09: Denuncias Ciudadanas
- ⚠️ UC-08: Cambio de Uso (reglas básicas)

### Fase 3: Post-MVP (después del lanzamiento)
- 🔜 UC-03: Análisis de Recurrencia
- 🔜 UC-04: Alertas por Capacidad
- 🔜 UC-05: Tendencias Históricas
- 🔜 UC-08: Cambio de Uso (ML avanzado)
- 🔜 UC-11: Reportes Históricos (v2)
- 🔜 UC-12: Registro de Visitantes (PWA + offline)
- 🔜 UC-13: Grilla de Incendios (básico)

---

## 📞 Contacto y feedback

Para sugerencias de nuevos casos de uso o mejoras:
- GitHub Issues: `github.com/forestguard/api/issues`
- Email: `contact@forestguard.ar`
- Community: `discord.gg/forestguard`

---

**Versión:** 4.0  
**Última actualización:** 2026-01-29  
**Autores:** ForestGuard Team