# Carrusel satelital de activos (UC-F08)

## Resumen

El carrusel satelital muestra, en la home del frontend, una selección de episodios activos y recientes con thumbnails satelitales en diferentes composiciones (RGB, SWIR, NBR). Es una de las principales puertas de entrada a la exploración visual de incendios.

## Caso de uso

- Ver rápidamente incendios relevantes con contexto geográfico claro.
- Acceder al detalle o a la exploración avanzada partiendo de un episodio del carrusel.

## Flujo técnico

1. Selección de episodios candidatos:
   - Se toman episodios `active` y `monitoring` desde `fire_episodes`.
   - Se usan los bounding boxes (`bbox_minx`, `bbox_miny`, `bbox_maxx`, `bbox_maxy`) para enmarcar la zona.
2. Selección de la mejor imagen Sentinel-2:
   - El backend consulta colecciones Sentinel-2 en Google Earth Engine.
   - Se filtra por nubosidad y se evalúa la cobertura espacial sobre el bbox.
3. Generación de thumbnails:
   - Se renderizan variantes RGB, SWIR y NBR sobre el bbox ajustado a formato 4:3.
   - Se suben los PNG generados a storage (S3/OCI).
4. Persistencia:
   - Se actualiza `fire_episodes.slides_data` con las URLs de thumbnails.
5. Consumo en frontend:
   - La home lee `slides_data` para construir el carrusel visible para la persona usuaria.

## Cobertura espacial en la selección de imágenes

La lógica de selección de imágenes utiliza un criterio de cobertura espacial para priorizar imágenes con mayor cantidad de píxeles válidos sobre el bbox.

- Se calcula la cobertura espacial como porcentaje de píxeles válidos en el área del episodio.
- Se define un umbral preferido de cobertura (por ejemplo, 95 %) para considerar una imagen como candidata ideal.
- Si no hay imágenes que cumplan el umbral, se elige la imagen con mejor cobertura disponible considerando también nubosidad y proximidad temporal.
- Implementación: método `_calculate_spatial_coverage` en `gee_service.py` con `reduceRegion` a scale=60 m; umbral por defecto 95 % (`min_coverage`); hasta 10 candidatas evaluadas. Script de prueba: `scripts/test_spatial_coverage.py`.

Esto evita que el carrusel muestre imágenes con poca área útil aunque tengan nubosidad extremadamente baja.

## Workers y servicios implicados

- **Workers**:
  - `worker-gee` ejecuta la tarea de generación de carrusel y se conecta a GEE.
- **Servicios backend**:
  - Servicio de episodios para obtener bounding boxes y estados.
  - `GEEService` para seleccionar y descargar imágenes.
  - Servicio de imágenes para generar y subir thumbnails a storage.

## Estado de implementación

- Pipeline técnico de carrusel operativo en producción.
- Thumbnails generados y actualizados diariamente para episodios activos y en monitoreo.
- Endurecimiento de la lógica de selección de imágenes con cobertura espacial y manejo de nubosidad completado.

Detalles históricos de la implementación de cobertura espacial en `get_best_image` están en `docs/archive/carousel/spatial_coverage_implementation.md`.
