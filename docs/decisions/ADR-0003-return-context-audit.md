# ADR-0003 — Origen `audit` en ReturnContext y límites de datos en sessionStorage

- **Estado**: Accepted  
- **Fecha**: 2026-03-16  

## Contexto

El frontend ya utilizaba un `ReturnContext` ligero para preservar el origen de navegación al detalle de incendio (`/fires/:id`) desde:

- Home/carrusel (`returnTo: 'home'`, preservando posición de scroll).
- Historial (`returnTo: 'history'`, preservando filtros vía querystring y scroll).
- Mapa (`returnTo: 'map'`, preservando el incendio seleccionado).

UC-F06 (página de auditoría `/audit`) requiere:

- Permitir navegar desde resultados de auditoría (`result.fires`) al detalle de incendio `/fires/:id`.
- Volver a `/audit` con los parámetros de búsqueda y página que dieron origen a la evidencia.
- Cumplir con la ley 25.326, evitando persistir resultados de auditoría o textos de búsqueda sensibles en `sessionStorage`.

## Decisión

Se extiende el tipo de retorno del frontend con un nuevo origen:

```ts
export type AuditReturnContext = {
  returnTo: 'audit'
  audit: {
    lat: number
    lon: number
    radius: number
    page: number
  }
}
```

Y se incluye en la unión de `ReturnContext`:

```ts
export type ReturnContext =
  | HomeReturnContext
  | HistoryReturnContext
  | MapReturnContext
  | AuditReturnContext
```

Reglas:

- Solo se guardan en `sessionStorage` los campos `lat`, `lon`, `radius` y `page` bajo la clave `RETURN_CONTEXT_KEY`.
- No se guardan:
  - Listas de resultados de auditoría.
  - Textos completos de búsqueda.
  - Ningún otro dato sensible de auditoría.
- `FireDetailPage` entiende el nuevo origen `audit` y, al pulsar “Volver”, navega a `/audit` pasando un `state.restore` con esos mismos parámetros numéricos.
- `AuditPage` reconstruye los filtros (`lat`, `lon`, `radius`) y la página a partir de `location.state.restore` cuando se ingresa desde un `ReturnContext.audit`.

## Consecuencias

- La navegación desde UC-F06 hacia `/fires/:id` y de vuelta queda alineada con el patrón existente de `ReturnContext` (home/history/map).
- El contexto de retorno de auditoría es completamente reconstruible a partir de parámetros compactos, sin almacenar información sensible ni resultados de auditoría en el almacenamiento del navegador.
- Se sienta la base para futuras extensiones de UC-F06 sin romper el contrato de navegación ni las restricciones de protección de datos.

