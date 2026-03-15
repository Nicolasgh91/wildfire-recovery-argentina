# Recuperación y cambio de uso (UC-F12)

## Resumen

El módulo de recuperación y cambio de uso (UC-F12) analiza la evolución de la vegetación después de un incendio y detecta posibles cambios de uso de suelo, apoyándose en Google Earth Engine y el motor interno VAE (Vegetation Analysis Engine).

## Casos de uso

- Monitorear la recuperación de la vegetación en eventos y episodios a lo largo del tiempo.
- Detectar cambios de uso (por ejemplo, construcción, agricultura o suelo desnudo) posteriores a un incendio.
- Generar reportes históricos con análisis de NDVI y evidencias satelitales.

## Flujo técnico de recuperación

1. Disparo del análisis:
   - Tareas programadas por Celery Beat para procesar eventos recientes y episodios relevantes.
   - Disparos manuales desde endpoints de monitoreo cuando no hay datos previos.
2. Motor de análisis:
   - `VAEService` calcula baseline NDVI preincendio y NDVI actual por mes.
   - Se obtiene un porcentaje de recuperación respecto al baseline y una clasificación de estado de recuperación.
3. Persistencia:
   - Los resultados se guardan en la tabla `vegetation_monitoring` con un registro por evento y fecha de monitoreo.
   - Se usan claves únicas y `ON CONFLICT` para garantizar idempotencia.
4. Exposición por API:
   - Endpoints de monitoreo devuelven series temporales, estados agregados por episodio y resúmenes para la interfaz de usuario.

## Flujo técnico de cambio de uso

1. Disparo del análisis:
   - Tareas periódicas que recorren eventos candidatos y encolan análisis de destrucción o cambio de uso.
2. Análisis:
   - `VAEService` compara baseline y NDVI actual, ventana temporal y área del evento.
   - Se infiere un tipo de cambio (por ejemplo, construcción, agricultura, suelo desnudo) con un nivel de confianza y severidad.
3. Persistencia:
   - Los resultados se guardan en `land_use_changes`, vinculados a cada evento y a registros de monitoreo.
4. Exposición:
   - Endpoints de monitoreo permiten consultar la lista de cambios y el recuento de posibles violaciones (`is_potential_violation`).

## Integración con reportes históricos

- El servicio de reportes históricos combina:
  - Análisis temporal de NDVI y recuperación proporcionado por `VAEService`.
  - Imágenes satelitales generadas por `GEEService`.
  - PDF con resumen ejecutivo, evidencias pre/postincendio y mecanismos de verificación.

## Workers y colas

- Workers de análisis se ejecutan en `worker-gee`, que es el único con credenciales GEE.
- Se utilizan colas dedicadas para las tareas intensivas de recuperación y cambio de uso.
- La tarea `recompute_baselines` (workers.tasks.backfill, cola `vae`) re-calcula baseline NDVI con el método mejorado (quality mosaic) para eventos que ya tienen registros en vegetation_monitoring, actualizando recovery_percentage y recovery_status sin volver a solicitar NDVI actual a GEE.

## Estado de implementación

- Motor VAE implementado y operativo con tablas y RLS configurados.
- Flujos de workers para recuperación y cambio de uso en funcionamiento, con tareas periódicas definidas.
- Endpoints de monitoreo expuestos para consultar series de recuperación y cambios de uso.
- Reportes históricos funcionando con integración a VAE y GEE.

Limitaciones y riesgos, así como deuda técnica detallada, se documentan en `docs/archive/ndvi-uf12/vae-flow-audit.md` y `docs/archive/ndvi-uf12/technical_debt_ucf12.md`.
