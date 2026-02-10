# Contrato de Feature Flags (UC-F07 y UC-F10)

> Objetivo: deshabilitar features completas en MVP sin depender solo de ocultar botones.
> Fuente de verdad: codigo actual en backend y frontend.

---

## Principios

1. Un flag se aplica en 3 capas:
- UI (sin accesos visibles)
- Routing frontend (URL directa -> 404)
- Backend/API (endpoint bloqueado -> 404)

2. Comportamiento esperado:
- Flag `false`: HTTP 404 con `{"detail":"Not available in MVP"}`.
- Flag `true`: feature disponible.

---

## Flags activos

### `FEATURE_CERTIFICATES` / `VITE_FEATURE_CERTIFICATES`

- Default MVP: `false`.
- Frontend bloquea ruta:
  - `/certificates`
- Backend bloquea router:
  - `/api/v1/certificates/*`

### `FEATURE_REFUGES` / `VITE_FEATURE_REFUGES`

- Default MVP: `false`.
- Frontend bloquea ruta:
  - `/shelters`
- Backend bloquea routers de refugios:
  - `/api/v1/visitor-logs*`
  - `/api/v1/shelters*`

---

## Variables de entorno

Backend `.env`:

```env
FEATURE_CERTIFICATES=false
FEATURE_REFUGES=false
```

Frontend `frontend/.env`:

```env
VITE_FEATURE_CERTIFICATES=false
VITE_FEATURE_REFUGES=false
```

---

## Validacion en deploy

- [ ] `/certificates` devuelve 404 en frontend.
- [ ] `/shelters` devuelve 404 en frontend.
- [ ] `/api/v1/certificates/verify/test` devuelve 404.
- [ ] `/api/v1/visitor-logs` devuelve 404.
- [ ] `/api/v1/shelters` devuelve 404.
- [ ] Navbar sin links a Certificates/Shelters.

---

## Habilitacion post-MVP

Para habilitar en un release posterior:

```env
# backend
FEATURE_CERTIFICATES=true
FEATURE_REFUGES=true

# frontend
VITE_FEATURE_CERTIFICATES=true
VITE_FEATURE_REFUGES=true
```

Reiniciar backend y frontend luego del cambio.
