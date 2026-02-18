# UI Debt Log

Decisiones y deuda técnica registrada durante el refactor de las cards del carrusel.

---

## 2026-02-13 — Refactor FireCard header

### `isImagePending` es un heuristic del FE

La condición actual:

```ts
const isImagePending = fire.slides_data == null || slidesToShow.length === 0
```

No distingue entre:
- "No hay thumbnails generados aún" (legítimo)
- "La request falló o todavía está cargando"

**Deuda**: el backend debería exponer un flag explícito `has_thumbnail: boolean` en `EpisodeListItem`.

### `formatProvincesLabel` y i18n

El helper genera strings inline (`"Chubut (+1)"`). Si el proyecto adopta i18n con interpolación (e.g. react-intl / i18next), migrar a template con placeholders:

```ts
t('provinces.label', { name: provinces[0], extra: provinces.length - 1 })
```

### Archivos legacy duplicados

Los siguientes archivos en `src/components/` parecen versiones anteriores y no se importan desde ningún lugar activo:

- `src/components/fire-card.tsx` — usa un tipo `Fire` de mock data, no `EpisodeListItem`.
- `src/components/FireCardSkeleton.tsx` — skeleton alternativo al inline en `fires/fire-card.tsx`.

**Acción**: verificar y eliminar si no tienen consumidores.
