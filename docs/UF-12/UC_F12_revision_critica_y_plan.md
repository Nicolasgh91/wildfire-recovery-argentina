# UC-F12: revisión crítica, validación y plan de corrección

> **Fecha:** 2026-02-24  
> **Alcance:** análisis de brechas lógicas, seguridad, UX/UI y plan de implementación  
> **Fuentes:** UC_F12_AS_IS_ANALYSIS, UC_F12_implementation_spec, UC_F12_critical_review, schema_v5, workers_documentation

---

## 1. Roadmap: estado actual vs. objetivo

```
ESTADO ACTUAL (AS-IS)                          OBJETIVO (TO-BE)
─────────────────────────────────────          ─────────────────────────────────
✅ Tablas vegetation_monitoring y               ✅ Mismas tablas con UNIQUE constraints,
   land_use_changes existen en BD                  RLS y FK
✅ VAEService implementado en backend           ✅ Workers funcionales que persisten datos
✅ Endpoints GET monitoring existen             ✅ Endpoints autenticados + rate-limited
✅ RecoveryPanel y RecoveryStatusBadge          ✅ UI Instagram-style con gráfico NDVI,
   existen en frontend                             badges, tarjetas de cambio de uso
⚠️ Workers son stubs (no persisten)            ✅ Workers reales con upsert idempotente
⚠️ Endpoints públicos sin JWT                  ✅ Auth obligatoria en todos los GET/POST
⚠️ Colas vae/analysis desalineadas            ✅ Cola vae con consumidor dedicado
❌ Sin UNIQUE constraints                      ✅ Idempotencia garantizada por schema
❌ Sin RLS en tablas de monitoreo              ✅ Políticas RLS cerradas para anon
❌ Badge con enums desalineados                ✅ Contrato único backend↔frontend
❌ Mapa sin marcadores de violación            ✅ Iconos diferenciados por violación
```

---

## 2. Fallas de lógica identificadas

### 2.1 Workers son stubs puros — CRÍTICO

Los archivos `recovery.py` y `destruction.py` retornan diccionarios con valores hardcodeados sin instanciar `VAEService`, sin consultar GEE y sin escribir en base de datos. Las tablas `vegetation_monitoring` y `land_use_changes` permanecen vacías.

Como workaround, el endpoint GET de recovery llama a `VAEService` en tiempo real (hasta 37 requests GEE por petición HTTP), lo que viola las restricciones de cuota del free tier y genera latencias de 10-30 segundos.

**Consecuencia en cascada:** toda la UI que lee de BD muestra "pending" permanentemente. El workaround en tiempo real es insostenible con más de un usuario concurrente.

### 2.2 Sin UNIQUE constraint para idempotencia — CRÍTICO

`vegetation_monitoring` no tiene constraint `UNIQUE(fire_event_id, monitoring_date)`. La PK es solo `id` (UUID autogenerado). `INSERT ... ON CONFLICT` no tiene sobre qué operar. Lo mismo aplica a `land_use_changes` con `(fire_event_id, change_detected_at)`.

### 2.3 Columna `anomaly_type` inexistente — ALTO

El endpoint `/monitoring/recovery/summary` referencia `vm.anomaly_type` en su query SQL, pero esa columna no existe en schema v5. El error se silencia con un catch genérico que retorna array vacío.

### 2.4 SQL INTERVAL no parametrizable — ALTO

En `monitoring.py:208`, el patrón `INTERVAL ':min_months months'` trata `:min_months` como texto literal. La query filtra incorrectamente o falla silenciosamente.

### 2.5 Fórmula de recovery_percentage simplificada — BAJO

Calcula `current_ndvi / baseline_ndvi * 100` en lugar de `(current - nadir) / (baseline - nadir) * 100`. No es un bug, pero la semántica debe documentarse explícitamente en la API.

### 2.6 FK `monitoring_record_id` sin constraint — MEDIO

La columna existe en `land_use_changes` pero no tiene constraint de clave foránea hacia `vegetation_monitoring(id)`.

---

## 3. Brechas de seguridad

### 3.1 Endpoints de monitoreo expuestos sin autenticación — CRÍTICO

El router de monitoring se monta en `main.py` sin `dependencies=[Depends(get_current_user)]`. Cualquier usuario anónimo puede acceder a datos de análisis de vegetación y cambios de uso de suelo. Esto viola la restricción 3.2 de la spec y el caso de prueba CT-UCF12-05.

**Comparación directa:** el router de reports SÍ tiene auth a nivel de router. Monitoring no.

### 3.2 RLS ausente en tablas de monitoreo — ALTO

Sin políticas RLS, el rol `anon` de Supabase tiene acceso directo a `vegetation_monitoring` y `land_use_changes`. La migración `2026_02_23_uc_f12_vae_monitoring.sql` existe en el repo pero no se ha confirmado su aplicación en producción.

### 3.3 Error messages exponen internos de GEE — BAJO

En `monitoring.py:423`, `str(e)` puede contener URLs internas, tokens de servicio o rutas de infraestructura de Google Earth Engine.

### 3.4 Endpoint POST /trigger sin implementar — CRÍTICO

No existe forma controlada de disparar procesamiento VAE. Sin rate limiting en el trigger, la cuota GEE queda desprotegida.

---

## 4. Riesgos y restricciones

| Riesgo | Severidad | Impacto | Mitigación |
|--------|-----------|---------|------------|
| Cola `vae` sin consumidor en docker-compose | Crítico | Jobs encolados se pierden | Agregar worker vae en compose |
| 37 req GEE por timeline en tiempo real | Crítico | Agota 50K req/día con ~1,350 usuarios | Migrar a lectura de BD + workers async |
| Crecimiento de vegetation_monitoring | Medio | 36 rows/evento/año → 500MB Supabase | Definir retención y purgado |
| Doble celery_app.py con rutas divergentes | Medio | Ambigüedad operacional | Consolidar en una sola configuración |
| Contrato de enums desalineado front↔back | Alto | Badge siempre muestra "sin monitoreo" | Unificar taxonomía de estados |
| Spec referencia rutas/archivos inexistentes | Bajo | Confusión en implementación | Actualizar spec |

---

## 5. UX/UI: análisis de experiencia tipo Instagram

### 5.1 Estado actual del frontend

El `RecoveryPanel` y `RecoveryStatusBadge` ya existen e integran en `FireDetail.tsx` con gate de autenticación. Sin embargo, presentan estos problemas:

**Badge con fallback permanente:** el backend emite estados como `excellent/good/moderate/poor/critical`, pero el badge espera enums VAE (`early_recovery`, `full_recovery`, etc.). Todo cae al fallback `not_started`, mostrando siempre "sin monitoreo" aunque haya datos.

**NdviChart con interfaz incompatible:** el componente espera `{ month: string, value: number }[]` pero la API retorna `{ month: int, ndvi_mean: float, recovery_percentage: float }`. No muestra línea de baseline ni gradiente de color por zona de recuperación.

**Feed sin badge de recovery:** el Home usa `components/fires/fire-card` (sin badge), no `components/fire-card.tsx` (que sí lo tiene). El badge documentado nunca se renderiza en el feed.

**Mapa sin diferenciación de violaciones:** los markers solo usan severity para color/ícono. El flag `is_potential_violation` no se inyecta desde `MapPage`.

### 5.2 Recomendaciones UX/UI estilo Instagram

Para captar la atención del usuario y fomentar la interacción:

- **RecoveryStatusBadge como chip visual:** usar gradientes de color (verde→amarillo→rojo) con microanimación de pulso para estados activos, similar a los stories de Instagram.
- **Gráfico NDVI interactivo:** implementar tooltips on-hover con `recovery_percentage`, zona de color por umbral de recuperación (verde/amarillo/rojo), línea punteada de baseline. Usar Framer Motion para transiciones al cargar datos.
- **Tarjetas de cambio de uso:** diseño tipo "card" con thumbnail de imagen satelital, badge de severidad, indicador visual de violación (borde rojo + ícono de alerta).
- **Skeleton loading:** mientras los datos se cargan, mostrar placeholders animados en lugar de spinners genéricos.
- **Empty state atractivo:** cuando no hay datos, mostrar ilustración + texto explicativo + CTA para que el admin ejecute el análisis, en lugar de solo "pending".

---

## 6. Preguntas de validación del flujo UC-F12

### 6.1 Obtención de datos

1. **¿Cuándo se ejecuta el análisis VAE?** Actualmente no hay scheduling automático (Celery Beat). Solo existe un trigger manual que encola a una cola `vae` sin consumidor activo. ¿Se confirmó que la migración de workers está aplicada en producción?

2. **¿De dónde obtiene la geometría el worker?** La spec asume que se lee `centroid` y `perimeter` de `fire_events`. ¿Estos campos están siempre poblados para eventos que necesitan análisis VAE?

3. **¿Qué pasa cuando GEE no tiene imagen disponible?** No hay manejo de nubosidad con ventana extendida (CT-UCF12-03). Un cloud_cover > 30% provoca excepción sin reintento.

4. **¿Los datos de episodios son correctos para VAE?** El `RecoveryPanel` se oculta en vista de episodio (`!isEpisodeDetail`). ¿Es correcto? ¿O los episodios también deberían mostrar datos agregados de recovery de sus eventos constituyentes?

5. **¿Cuál es la fuente de verdad para baseline_ndvi?** Se calcula en `VAEService` usando una imagen pre-incendio. ¿Se persiste una sola vez o se recalcula en cada ejecución del worker?

### 6.2 Presentación de datos

6. **¿Qué páginas muestran datos VAE?** Actualmente solo `/fires/:id` (detalle de evento). El feed (`/`), el mapa (`/map`) y el historial (`/fires/history`) no consumen datos VAE. ¿Es intencional?

7. **¿El endpoint summary tiene consumidor frontend?** `GET /monitoring/recovery/summary` existe pero ningún componente lo llama. ¿Debe eliminarse o integrarse en alguna vista?

8. **¿Los datos de la tabla `vegetation_monitoring` son correctos?** Actualmente la tabla está vacía porque los workers son stubs. El endpoint GET hace llamadas GEE en tiempo real como workaround. ¿Los datos que genera `VAEService` en tiempo real fueron validados contra ground truth?

9. **¿Es correcto que la sección de recovery sea invisible para usuarios no autenticados?** La página `/fires/:id` es pública, pero el `RecoveryPanel` solo se renderiza con sesión activa. ¿Un ciudadano sin cuenta debería poder ver al menos el estado de recuperación?

10. **¿Qué muestra el NdviChart cuando hay datos parciales?** Si solo hay 3 de 36 meses, ¿el gráfico muestra solo esos puntos o extrapola?

### 6.3 Actualización de datos

11. **¿Con qué frecuencia se deben actualizar los datos NDVI?** La spec habla de monitoreo mensual por 36 meses. ¿Es mensual exacto o se adapta a disponibilidad de imágenes satelitales?

12. **¿Existe un mecanismo de backfill?** Si un evento tiene 6 meses sin datos, ¿el worker procesa los 6 meses faltantes en una sola ejecución o uno por vez?

13. **¿Cómo se maneja la idempotencia sin UNIQUE constraint?** Sin `ON CONFLICT`, ejecuciones repetidas del worker generarían duplicados. ¿Se implementó algún mecanismo de deduplicación a nivel de aplicación?

14. **¿Qué pasa cuando la migración de hardening se aplica?** La migración `2026_02_23_uc_f12_vae_monitoring.sql` agrega UNIQUE constraints, NOT NULL, FK y RLS. ¿Se verificó que no hay datos inconsistentes previos que bloqueen la migración?

15. **¿La retención de datos está planificada?** Con 36 registros/evento/año, la tabla crece linealmente. ¿Se definió una política de purgado o archivado para respetar el límite de 500MB de Supabase?

---

## 7. Plan de corrección e implementación

### Fase 0 — Prerrequisitos de schema (bloqueante)

| # | Tarea | Archivos | Esfuerzo |
|---|-------|----------|----------|
| 0.1 | Aplicar migración de hardening (UNIQUE, NOT NULL, FK, RLS) | `2026_02_23_uc_f12_vae_monitoring.sql` | ~15 min |
| 0.2 | Verificar que no hay datos inconsistentes previos | Query de validación en producción | ~10 min |
| 0.3 | Confirmar RLS activa con `pg_policies` | Verificación SQL | ~5 min |

### Fase 1 — Backend: corregir flujo de datos (prioridad máxima)

| # | Tarea | Archivos | Esfuerzo |
|---|-------|----------|----------|
| 1.1 | Reescribir `recovery.py` para usar VAEService + persistir con upsert | `workers/tasks/recovery.py` | ~80 líneas |
| 1.2 | Reescribir `destruction.py` para usar VAEService + persistir | `workers/tasks/destruction.py` | ~60 líneas |
| 1.3 | Consolidar `celery_app.py` (eliminar doble config, definir cola `vae`) | `celery_app.py`, `workers/celery_app.py` | ~30 líneas |
| 1.4 | Agregar worker `vae` en docker-compose | `docker-compose.yml` | ~20 líneas |
| 1.5 | Reemplazar `anomaly_type` por `activity_type` en query de summary | `app/api/routes/monitoring.py:196` | ~10 líneas |
| 1.6 | Corregir INTERVAL parametrización en summary | `app/api/routes/monitoring.py:208` | ~5 líneas |
| 1.7 | Implementar reintento con ventana extendida por nubosidad | `app/services/vae_service.py` | ~20 líneas |

### Fase 2 — Seguridad (prioridad alta, paralela a fase 1)

| # | Tarea | Archivos | Esfuerzo |
|---|-------|----------|----------|
| 2.1 | Agregar `dependencies=[Depends(get_current_user)]` al router monitoring | `app/main.py` | ~3 líneas |
| 2.2 | Sanitizar error messages (no exponer `str(e)` de GEE) | `app/api/routes/monitoring.py` | ~10 líneas |
| 2.3 | Implementar `POST /trigger` con auth admin + rate limit | `app/api/routes/monitoring.py` | ~40 líneas |
| 2.4 | Agregar tarea Celery Beat para procesamiento periódico VAE | `celery_app.py` | ~15 líneas |

### Fase 3 — Frontend: alinear contratos y UX Instagram-style

| # | Tarea | Archivos | Esfuerzo |
|---|-------|----------|----------|
| 3.1 | Unificar taxonomía de estados recovery (back↔front) | Badge config + endpoint classifier | ~30 líneas |
| 3.2 | Adaptar `NdviChart` al formato real de API + baseline + gradiente | `ndvi-chart.tsx` | ~40 líneas |
| 3.3 | Integrar `RecoveryStatusBadge` en el fire-card activo del feed | `components/fires/fire-card.tsx` | ~15 líneas |
| 3.4 | Agregar marcador diferenciado en mapa para violaciones | `FireMarkers.tsx` + `MapPage.tsx` | ~25 líneas |
| 3.5 | Implementar skeleton loading y empty state atractivo | `RecoveryPanel.tsx` | ~40 líneas |
| 3.6 | Diseñar `LandUseChangeCard` con thumbnail + badge severidad | Nuevo componente | ~50 líneas |

### Fase 4 — Escalabilidad y observabilidad

| # | Tarea | Archivos | Esfuerzo |
|---|-------|----------|----------|
| 4.1 | Migrar endpoint GET recovery de GEE-en-tiempo-real a lectura de BD | `monitoring.py` | ~30 líneas |
| 4.2 | Definir estrategia de backfill con batching | `workers/tasks/recovery.py` | ~30 líneas |
| 4.3 | Definir política de retención para vegetation_monitoring | Migración + docs | ~15 líneas |
| 4.4 | Resolver conflicto de nomenclatura UC-12 vs UC-F12 en OpenAPI tags | `app/main.py` | ~10 líneas |

### Orden de ejecución y dependencias

```
Fase 0 ──→ Fase 1 ──→ Fase 4.1
              │
              └──→ Fase 2 (paralela)
                      │
                      └──→ Fase 3 (después de 1 + 2)
                              │
                              └──→ Fase 4.2-4.4
```

### Criterios de verificación por fase

**Fase 0:** `SELECT conname FROM pg_constraint WHERE conrelid = 'vegetation_monitoring'::regclass AND contype = 'u'` retorna `uq_vm_event_date`. RLS activa en ambas tablas.

**Fase 1:** Worker ejecutado dos veces para el mismo evento produce la misma cantidad de rows (idempotencia). `GET /monitoring/recovery/{id}` retorna datos desde BD, no desde GEE en tiempo real.

**Fase 2:** `curl` sin JWT a cualquier endpoint de monitoring retorna 401. `POST /trigger` sin admin retorna 403. Mensajes de error no contienen URLs de GEE.

**Fase 3:** Badge muestra estado correcto según datos del backend. NdviChart renderiza con datos parciales. Mapa muestra ícono diferenciado para violaciones.

---

## 8. Resumen ejecutivo de hallazgos

Se identificaron **4 problemas críticos** que bloquean el funcionamiento correcto de UC-F12:

1. **Workers vacíos:** el pipeline de datos está roto desde el origen — las tablas nunca reciben datos.
2. **Sin idempotencia:** no hay UNIQUE constraints para soportar upserts seguros.
3. **Sin autenticación:** los endpoints de monitoreo son públicos, exponiendo datos sensibles.
4. **Cola sin consumidor:** el trigger encola jobs a `vae` pero ningún worker los consume.

La buena noticia: la infraestructura base existe (tablas, VAEService, componentes UI, migración de hardening). El esfuerzo estimado total es de aproximadamente **~600 líneas de código** distribuidas en 4 fases secuenciales con las fases 1 y 2 ejecutables en paralelo.
