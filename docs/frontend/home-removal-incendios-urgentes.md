# Cambio en Home: eliminación de sección Incendios Urgentes

**Fecha:** 2026-02-26

Por decisión de producto se eliminó la sección "Incendios Urgentes" (barra horizontal superior) de la página Home (`/home`).

- **Antes:** La home mostraba arriba una barra con episodios activos de alta severidad (FRP ≥ 50) y enlaces a detalle.
- **Después:** El primer contenido visible en la home es el título "Incendios activos en Argentina", filtros y grid de tarjetas. Los mismos episodios siguen accesibles desde el grid.

Cambios técnicos: eliminado el componente `stories-bar.tsx`, su uso en `Home.tsx` y la clave i18n `urgentFires` en ES/EN.
