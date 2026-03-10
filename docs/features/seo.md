# Seo y geo

## Resumen

Este módulo agrupa las capacidades relacionadas con visibilidad, estructura de rutas y comportamiento geo en el frontend, así como los endpoints públicos que soportan estas experiencias.

## Rutas y acceso

- Rutas públicas destinadas a contenido y soporte (`/faq`, `/manual`, `/glossary`, `/contact`, `/citizen-report`).
- Rutas públicas de datos agregados (`/map`, partes de `/home`) que consumen endpoints abiertos de incendios y estadísticas.
- Rutas protegidas que requieren sesión para exploración avanzada y vistas detalladas.

La matriz completa de acceso por ruta está en `docs/frontend/routing_access_ruc.md`.

## Contratos API relevantes

- Endpoints públicos:
  - `GET /api/v1/fires`: listado de incendios.
  - `GET /api/v1/fires/stats`: estadísticas agregadas (con API key o JWT).
  - `GET /api/v1/fires/export`: export de dataset.
- Endpoints asociados a contenido y visibilidad:
  - `POST /api/v1/contact`: formulario de contacto público.

La matriz de autenticación por endpoint se detalla en `docs/backend/api/auth_matrix.md`.

## Comportamiento geoespacial en frontend

- El mapa principal consume episodios activos y recientes para mostrar incendios en curso y recientes.
- Las rutas de exploración y detalle utilizan parámetros geográficos para centrar mapas y vistas.

## Estado de implementación

- Rutas y acceso alineados con la matriz de routing y autenticación actual.
- Endpoints públicos disponibles para consumo de mapas y contenido.

Para una descripción más detallada de UX y narrativa de producto, ver `docs/product/README.md` y `docs/product/estado-real-del-producto.md`.
