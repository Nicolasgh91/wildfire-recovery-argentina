# frontend de Vestigia

Frontend en React + Vite para exploracion guiada de incendios historicos.

## estado general

El frontend esta productivo para los flujos principales (exploracion, historial, mapa, login, pagos base), con algunos modulos en estado parcial.

## rutas y estado por pantalla

| ruta | objetivo para usuario | estado | notas |
|---|---|---|---|
| `/` | puerta de entrada | ✅ | redirige segun sesion (`/login` o `/home`) |
| `/login`, `/register`, `/auth/callback` | autenticacion | ✅ | email, OTP y Google OAuth |
| `/home` | resumen inicial | ✅ | usa datos reales de episodios |
| `/map` | visualizacion geoespacial | ✅ | episodios reales (activos + recientes) |
| `/exploracion` | flujo guiado de investigacion | ✅ | crea borrador, calcula costo, genera HD y muestra PDF |
| `/reports` | compatibilidad legacy | ✅ | redireccion a `/exploracion` |
| `/fires/history` | historico y dashboard | ✅ | protegido por auth |
| `/fires/:id` | detalle de incendio | 🟡 | datos principales disponibles; piezas UX aun en ajuste |
| `/audit` | verificar terreno (modulo avanzado) | ✅ | protegido por auth |
| `/credits` | compra y saldo de creditos | 🟡 | flujo operativo con caveats de retorno/estado |
| `/payments/return` | retorno de checkout | 🟡 | depende rehidratacion de sesion y estado de pago |
| `/citizen-report` | reporte ciudadano | 🟡 | UX activa, envio final aun simulado |
| `/certificates` | certificados | 🟡 | feature flag + frontend mock |
| `/shelters` | refugios/visitantes | 🟡 | feature flag por defecto desactivada |
| `/faq`, `/manual`, `/glossary`, `/contact` | contenido y soporte | ✅ | acceso publico |

## estados de integracion relevantes

### ✅ integracion completa o estable

- enrutado y proteccion de rutas
- autenticacion con Supabase
- exploracion (create/list/update/items/quote/generate/assets)
- historial de incendios y estadisticas
- mapa con episodios reales

### 🟡 integracion parcial o con caveats

- MercadoPago: operativo con dependencia de webhook + retorno de sesion
- Citizen report: pendiente de cableado completo backend para submit final
- Certificates: backend existe, frontend en modo mock y ruta por flag
- Shelters: ruta y backend disponibles, uso controlado por flag

## contratos API usados por frontend

### exploracion

- `POST /api/v1/explorations/`
- `GET /api/v1/explorations/`
- `GET /api/v1/explorations/{id}`
- `PATCH /api/v1/explorations/{id}`
- `POST /api/v1/explorations/{id}/items`
- `DELETE /api/v1/explorations/{id}/items/{item_id}`
- `POST /api/v1/explorations/{id}/quote`
- `POST /api/v1/explorations/{id}/generate`
- `GET /api/v1/explorations/{id}/generate/{job_id}`
- `GET /api/v1/explorations/{id}/assets`

### reportes y pagos

- `POST /api/v1/reports/judicial`
- `POST /api/v1/reports/historical`
- `POST /api/v1/payments/checkout`
- `GET /api/v1/payments/pricing`
- `GET /api/v1/payments/{payment_request_id}`
- `GET /api/v1/payments/credits/balance`
- `GET /api/v1/payments/credits/transactions`

### historico y mapa

- `GET /api/v1/fires`
- `GET /api/v1/fires/stats`
- `GET /api/v1/fires/export`
- `GET /api/v1/fire-episodes?mode=active|recent`

## feature flags

- `VITE_FEATURE_CERTIFICATES=false` (default en ejemplo)
- `VITE_FEATURE_REFUGES=false` (default en ejemplo)

Fuente: `frontend/.env.example` y `frontend/src/lib/featureFlags.ts`.

## referencia cruzada

- estado producto: `docs/product/estado-real-del-producto.md`
- casos de uso: `docs/product/casos-de-uso-y-estado.md`
- auth por endpoint: `docs/backend/api/auth_matrix.md`
