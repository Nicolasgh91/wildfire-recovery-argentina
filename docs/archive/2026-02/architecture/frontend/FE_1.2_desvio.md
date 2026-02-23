# FE_1.2_desvio

Fecha: 2026-02-04

## Contexto
Durante la integracion de FE-1.2 (FireDetail + QualityIndicator) se necesitaba
consumir `GET /api/v1/fires/{id}` desde el frontend. Este endpoint estaba
definido en la hoja tecnica frontend, pero no figuraba explicitamente en la
arquitectura final del backend.

En paralelo, se detecto un desfasaje entre el ORM y la tabla real
`fire_climate_associations` (T0.2) y `climate_data` (T0.1). El ORM intentaba
leer columnas inexistentes, provocando errores 500 en FireDetail.

## Desvio aplicado
- Se habilito el endpoint `GET /api/v1/fires/{id}` para soportar FireDetail.
- Se alinearon los modelos ORM `FireClimateAssociation` y `ClimateData` con las
  migraciones T0.2 y T0.1 respectivamente (columnas reales y claves correctas).
- Se ajusto la relacion en `FireEvent` a N:M (`climate_associations`).

## Impacto
- No hay cambios de schema en la base de datos (solo ORM).
- Se elimina el 500 al consultar `/api/v1/fires/{id}` con datos climaticos.
- Requiere reiniciar el backend para cargar los modelos actualizados.

## Archivos involucrados
- `app/api/v1/fires.py`
- `app/services/fire_service.py`
- `app/models/climate.py`
- `app/models/fire.py`
