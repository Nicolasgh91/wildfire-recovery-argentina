# ForestGuard — Refactorización gee_service.py

## ForestGuard

# Refactorización de gee_service.py  
Análisis de viabilidad, alcance y plan de ejecución

**Versión 1.0 — Marzo 2026**  
**Clasificación: interno — equipo de desarrollo**

---

# 1. Evaluación del análisis de errores

El análisis realizado sobre gee_service.py (commit 6e495345) identifica correctamente los problemas estructurales del módulo. A continuación se evalúa cada hallazgo con su nivel de criticidad real en el contexto de ForestGuard sobre Oracle Cloud (1 GB RAM, 947 MB efectivos).

## 1.1 Hallazgos confirmados como críticos

**Thumbnails con franjas vacías:** el problema reportado de franjas verticales vacías se origina en la interacción entre _compute_safe_scale, el bbox del episodio y el parámetro dimensions. Cuando el aspect ratio del bbox no coincide con el de dimensions (p. ej. bbox cuadrado + dimensions "768x576"), GEE rellena con píxeles vacíos. El fix requiere calcular dimensions dinámicamente a partir del aspect ratio del bbox.

**Bug acquisition_date None:** get_collection_info asigna None a un campo tipado como date (no Optional[date]). En producción esto puede generar TypeError en downstream cuando imagery_service intenta formatear la fecha para slides_data.

**Inconsistencia sun_elevation vs zenith:** get_collection_info guarda el ángulo cenital crudo, pero get_image_metadata lo convierte a elevación (90 - zenith). Consumidores que asumen "siempre elevación" obtienen datos inconsistentes.

**Duplicación get_gee_service en historical.py:** existe una factory duplicada que puede divergir de la centralizada. Riesgo real de bugs silenciosos si se actualiza una y no la otra.

---

## 1.2 Hallazgos confirmados de prioridad media

**Lógica de retry duplicada:** los métodos get_thumbnail_url, get_dnbr_thumbnail_url y download_thumbnail repiten ~25 líneas idénticas de retry con backoff exponencial. Tres copias del mismo patrón aumentan el riesgo de regresiones.

**Geometría bbox repetida 10+ veces:** ee.Geometry.Rectangle([bbox["west"], bbox["south"], bbox["east"], bbox["north"]]) aparece en prácticamente todos los métodos. Un cambio de CRS o validación requeriría tocar todos los sitios.

**Parsing de dimensions duplicado:** la lógica "si es string con x, pasar tal cual; si no, convertir a int" aparece en get_thumbnail_url y get_dnbr_thumbnail_url sin reutilización.

**Código muerto:** import de lru_cache sin uso, dataclass ImageResult exportada pero nunca instanciada, y bloques de debug logging (_debug_log) que no deberían llegar a producción.

---

## 1.3 Hallazgos de prioridad baja (correctos pero diferibles)

Las observaciones sobre violaciones SOLID (SRP/OCP/ISP/DIP), el Singleton frágil y la falta de Strategy pattern son arquitectónicamente válidas. Sin embargo, en el contexto actual de ForestGuard (equipo reducido, VM con recursos limitados, ~10 episodios activos) el costo de un refactor completo con protocolos abstractos y DI excede el beneficio inmediato. Se propone una extracción incremental por fases sin sobreingeniería.

---

# 2. Análisis de viabilidad

## 2.1 Restricciones del entorno

### Restricción  
RAM: 947 MB efectivos  

### Impacto en la refactorización  
No se pueden agregar contenedores ni aumentar concurrencia. El refactor debe mantener exactamente 2 workers (fast + gee) con concurrency=1.

---

### Restricción  
Cuota GEE free tier  

### Impacto en la refactorización  
50.000 req/día. El rate limiting a 1 req/s debe preservarse. Los tests de regresión no deben consumir cuota (usar mocks).

---

### Restricción  
Deploy automatizado  

### Impacto en la refactorización  
CI/CD via GitHub Actions (3 workflows). Cambios en gee_service.py disparan backend-build.yml → deploy-prod-vm.yml. El refactor no debe requerir cambios en los workflows.

---

### Restricción  
6 consumidores directos  

### Impacto en la refactorización  
imagery_service, vae_service, ers_service, closure_report_service, exploration_hd_worker y historical router. Todas las firmas públicas deben permanecer estables.

---

### Restricción  
Supabase 500 MB  

### Impacto en la refactorización  
Sin impacto directo: el refactor no modifica schema ni agrega tablas.

---

## 2.2 Evaluación de viabilidad por fase

Se propone un refactor en 3 fases con gates de validación entre cada una. Cada fase es desplegable de forma independiente y ofrece valor inmediato sin romper funcionalidad existente.

### Fase 1  
**Alcance:** Corregir bugs activos y eliminar código muerto  
**Esfuerzo:** 4-6 horas  
**Riesgo:** Bajo  
**Viabilidad:** Alta. Cambios quirúrgicos sin reestructuración.

### Fase 2  
**Alcance:** Extraer helpers y eliminar duplicación  
**Esfuerzo:** 6-8 horas  
**Riesgo:** Medio-bajo  
**Viabilidad:** Alta. Refactors internos sin cambio de API pública.

### Fase 3  
**Alcance:** Extraer módulos y reducir God class  
**Esfuerzo:** 10-14 horas  
**Riesgo:** Medio  
**Viabilidad:** Media-alta. Requiere actualizar imports en 6 consumidores.

---

# 3. Dependencias y referencias afectadas

## 3.1 Mapa de consumidores

### imagery_service.py  
Métodos utilizados: get_sentinel_collection, get_best_image, get_thumbnail_url, download_thumbnail  
Impacto del refactor: Fase 1-2: ninguno (firmas estables). Fase 3: actualizar import si se extrae ThumbnailService.

### vae_service.py  
Métodos utilizados: calculate_ndvi, get_sentinel_collection, get_best_image, get_image_cloud_cover  
Impacto del refactor: Fase 1: fix sun_elevation impacta si VAE consume metadata. Fase 3: actualizar import si se extrae IndexService.

### ers_service.py  
Métodos utilizados: calculate_ndvi, calculate_nbr, get_dnbr_thumbnail_url, download_dnbr_thumbnail  
Impacto del refactor: Fase 2: beneficiado por retry unificado. Fase 3: actualizar imports.

### closure_report_service.py  
Métodos utilizados: download_thumbnail, get_sentinel_collection  
Impacto del refactor: Fase 1-2: ninguno. Fase 3: mínimo.

### exploration_hd_worker.py  
Métodos utilizados: get_thumbnail_url, download_thumbnail  
Impacto del refactor: Fase 1-2: ninguno. Fase 3: actualizar import.

### historical.py (router)  
Métodos utilizados: get_gee_service (duplicada localmente)  
Impacto del refactor: Fase 1: eliminar factory duplicada y usar la centralizada.

---

# 4. Alcance detallado de los cambios

## 4.1 Fase 1: corrección de bugs (prioridad alta)

Objetivo: resolver los problemas que afectan directamente la calidad de thumbnails y la estabilidad de datos en producción. Todos los cambios son quirúrgicos, sin reestructuración.

### F1-01. Fix thumbnails con franjas vacías  
Archivo: app/services/gee_service.py  
Problema: cuando el aspect ratio del bbox del episodio difiere del de dimensions, GEE genera franjas vacías.  
Solución: calcular dimensions dinámicamente respetando el aspect ratio del bbox con nueva función _bbox_to_dimensions(bbox, max_dim=768).  
Regresión: los thumbnails cambiarán ligeramente de proporción. No se pierden datos.

### F1-02. Fix acquisition_date Optional  
Archivo: app/services/gee_service.py (dataclass ImageMetadata, línea 204)  
Cambio: acquisition_date: date → acquisition_date: Optional[date] = None  
Regresión: ninguna.

### F1-03. Unificar sun_elevation  
Archivo: app/services/gee_service.py (método get_collection_info, línea 557)  
Cambio: reemplazar zenith crudo por elevación (90 - zenith).  
Regresión: bajo.

### F1-04. Eliminar factory duplicada  
Archivo: app/api/routes/historical.py  
Cambio: usar import centralizado de get_gee_service.  
Regresión: ninguna.

### F1-05. Eliminar código muerto  
Remover import lru_cache, bloques _debug_log y evaluar ImageResult.

---

# 5. Regresiones, restricciones y riesgos

## 5.1 Matriz de riesgos

R-01: Fix de aspect ratio cambia tamaño visual de thumbnails existentes.  
Mitigación: force_refresh del carousel post-deploy.

R-02: Fase 3 rompe imports.  
Mitigación: __init__.py re-exporta todo.

R-03: Retry helper cambia timing.  
Mitigación: Unit tests con mock de sleep.

R-04: Memory pressure en deploy.  
Mitigación: Monitorear con docker stats.

R-05: GEE quota excedida en testing.  
Mitigación: Tests con mocks.

---

# 6. Roadmap de ejecución

## 6.1 Estado actual vs. objetivo

Estado actual: ~1370 líneas en un único archivo.  
Objetivo: ~200 líneas por módulo en 7-8 archivos.  
Duplicación eliminada.  
0 bugs conocidos.  
Código muerto eliminado.  
Mejor testabilidad y extensibilidad.

---

## 6.2 Cronograma propuesto

Fase 1: Bugfix + limpieza (4-6 horas)  
Gate 1: Tests F1 pasan + deploy.

Fase 2: DRY + helpers (6-8 horas)  
Gate 2: Tests F2 pasan + deploy.

Fase 3: Separación + fachada (10-14 horas)  
Gate 3: Tests F3 pasan + deploy.

Esfuerzo total estimado: 24-32 horas.

---

# 7. Propuesta arquitectónica

## 7.1 Diagrama de dependencias objetivo

GEEService (fachada orquestadora) compone:  
GEEAuthenticator  
GEECollectionService  
GEEIndexService  
GEEThumbnailService  
GEETimeSeriesService  

Mantiene compatibilidad hacia atrás.

---

## 7.2 Patrón Strategy para visualizaciones

Registry de estrategias en lugar de cadena if/elif.

RGB, FALSE_COLOR, SWIR, IMPACT, REALITY → BandSelectionStrategy  
NDVI → NormalizedDifferenceStrategy("B8","B4")  
NBR, SCIENCE, BURN_SEVERITY → NormalizedDifferenceStrategy("B8","B12")

Cumple Open/Closed.

---

# 8. Conclusión

El análisis es técnicamente sólido. La refactorización en 3 fases permite mejoras incrementales sin comprometer producción.

La fase 1 es prioritaria y resuelve el problema visible de thumbnails con franjas vacías.

Las fases 2 y 3 reducen deuda técnica y mejoran mantenibilidad y extensibilidad futura.

Página