# casos de uso y estado real

Fecha de corte: 22 de febrero de 2026.

Este documento es la fuente canonica de casos de uso de Vestigia.

Fuente base utilizada:

- `docs/casos de uso/casos_de_uso.md` (estructura UC y mapeo historico)
- validacion contra codigo actual (`app/**`, `frontend/src/**`) y docs de contratos (`docs/backend/api/auth_matrix.md`)

## lectura rapida

Vestigia hoy esta orientado a exploracion guiada de incendios historicos con evidencia satelital.

- foco principal: explorar, comparar, entender contexto y generar evidencia
- modulo avanzado: verificacion de terreno con lectura legal
- capacidades en consolidacion: pagos, certificados y flujos avanzados para instituciones

## tabla unica de casos de uso y estado

| UC | nombre actual | origen | estado | que puede hacer hoy | evidencia principal |
|---|---|---|---|---|---|
| UC-F01 | Contacto y soporte | inicial | ✅ listo en produccion | formulario publico con adjuntos y endpoint activo | `app/api/v1/contact.py`, `frontend/src/pages/contact.tsx` |
| UC-F02 | Estadisticas publicas agregadas | inicial | ✅ listo en produccion | metricas publicas agregadas sin login | `README.md`, `docs/flujo-deploy.md` |
| UC-F03 | Historico y dashboard | inicial | ✅ listo en produccion | filtros, estadisticas y export en historial | `frontend/src/pages/FireHistory.tsx`, `app/api/v1/fires.py` |
| UC-F04 | Calidad y confiabilidad del dato | inicial | 🟡 implementado con caveats | metricas de calidad disponibles por API; visibilidad en UI parcial | `app/main.py` (tag quality), `frontend/src/pages/FireDetail.tsx` |
| UC-F05 | Recurrencia y tendencias | inicial | 🟡 implementado con caveats | endpoints de analisis disponibles; UX general en evolucion | `app/main.py` (tag analysis), `app/api/routes/episodes.py` |
| UC-F06 | Verificar terreno (modulo avanzado legal) | inicial renombrado | ✅ listo en produccion | consulta de terreno con evidencia y contexto legal | `frontend/src/pages/Audit.tsx`, `app/api/v1/audit.py` |
| UC-F07 | Registro de visitantes/refugios | inicial | 🟡 implementado con caveats | backend y pantalla existen; feature flag por defecto desactivada | `app/api/routes/visitor_logs.py`, `frontend/src/App.tsx` |
| UC-F08 | Carrusel satelital de activos | inicial | ✅ listo en produccion | thumbnails operativos y refresco de imagery | `app/services/imagery_service.py`, `workers/tasks/carousel_task.py` |
| UC-F09 | Reporte de cierre pre/post | inicial | 🟡 implementado con caveats | pipeline tecnico disponible; visibilidad producto acotada | `app/workers/fire_worker.py`, `docs/backend/workers/workers_documentation.md` |
| UC-F10 | Certificados monetizados | inicial | 🟡 implementado con caveats | backend existe con flag/API key; UI publica sigue mock y flag off | `app/api/routes/certificates.py`, `frontend/src/pages/Certificates.tsx` |
| UC-F11 | Exploracion y reportes especializados | inicial ampliado | ✅ listo en produccion | wizard de exploracion, assets HD, PDF y reportes judicial/historico | `frontend/src/pages/Exploration.tsx`, `app/api/v1/explorations.py`, `app/api/routes/reports.py`, `workers/tasks/pdf_generation_task.py` |
| UC-F12 | Recuperacion y cambio de uso (VAE) | inicial | ⏳ en progreso | base tecnica presente, no expuesto como flujo de producto maduro | `app/services/vae_service.py`, `app/main.py` |
| UC-F13 | Episodios macro y metadata reproducible | inicial | ✅ listo en produccion | agrupacion macro y base reproducible para exploracion/imagenes | `app/models/episode.py`, `app/api/routes/episodes.py`, `workers/tasks/clustering_task.py` |

## casos agregados o ampliados durante el rediseño

| tema | cambio incorporado | estado | evidencia |
|---|---|---|---|
| login y acceso | raiz con gate (`/`), login + google, rutas protegidas y rutas publicas claras | ✅ | `frontend/src/App.tsx`, `docs/frontend/routing_access_ruc.md` |
| mercado pago | checkout, pricing, retorno, balance y transacciones de creditos | 🟡 | `app/api/v1/payments.py`, `frontend/src/pages/Credits.tsx`, `frontend/src/pages/PaymentReturnPage.tsx` |
| exploracion (ex reports/certificados como narrativa) | consolidacion en `/exploracion` y alias legacy `/reports` | ✅ | `frontend/src/App.tsx`, `frontend/src/pages/Exploration.tsx` |
| verificar terreno (renombre UX) | se mantiene capacidad legal, pero posicionada como modulo avanzado | ✅ | `frontend/src/pages/Audit.tsx`, `app/api/v1/audit.py` |

## limites honestos (sin sobrepromesas)

- MercadoPago funciona, pero se considera en maduracion operativa por dependencias de webhook, sesion y entorno.
- Citizen report en frontend aun usa flujo mock para envio.
- Certificates en frontend aun esta en modo mock y con feature flag.
- Shelters/visitor logs estan disponibles en backend y ruta, pero se operan con flag por defecto desactivada.

## decision de canon

- Canon oficial de casos de uso: este archivo.
- Fuente historica de redaccion original: `docs/casos de uso/casos_de_uso.md` (migrado a puente).
