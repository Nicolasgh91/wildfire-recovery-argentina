# Vestigia — matriz de autenticacion por endpoint

Fuente: contrato vigente en codigo + validacion de pruebas de auth.

## matriz principal

| metodo | endpoint | auth | nota |
|---|---|---|---|
| `POST` | `/api/v1/reports/judicial` | JWT | reporte judicial especializado |
| `POST` | `/api/v1/reports/historical` | JWT | reporte historico |
| `GET` | `/api/v1/reports/{id}/verify` | JWT | verificacion de reporte |
| `POST` | `/api/v1/explorations/` | JWT | crear borrador de exploracion |
| `GET` | `/api/v1/explorations/` | JWT | listar exploraciones del usuario |
| `POST` | `/api/v1/audit/land-use` | JWT | verificar terreno (modulo avanzado) |
| `POST` | `/api/v1/payments/checkout` | JWT | crear checkout |
| `GET` | `/api/v1/payments/{payment_request_id}` | JWT | consultar estado de pago |
| `GET` | `/api/v1/payments/credits/balance` | JWT | saldo de creditos |
| `GET` | `/api/v1/payments/credits/transactions` | JWT | movimientos de creditos |
| `GET` | `/api/v1/fires` | Publico | listado de incendios |
| `GET` | `/api/v1/fires/{id}` | Publico | detalle de incendio |
| `GET` | `/api/v1/fires/stats` | API Key o JWT | estadisticas agregadas |
| `GET` | `/api/v1/fires/export` | API Key o JWT | export de dataset |
| `POST` | `/api/v1/contact` | Publico | formulario de contacto |
| `GET` | `/health` | Publico | healthcheck |
| `GET` | `/api/v1/quality/fire-event/{id}` | API Key | metricas de calidad |
| `GET` | `/api/v1/certificates/*` | API Key + feature flag | certificados (modulo acotado) |
| `*` | `/api/v1/alerts/*` | API Key | endpoints internos |
| `*` | `/api/v1/workers/*` | API Key | endpoints de workers |
| `*` | `/api/v1/tasks/*` | API Key | tareas de mantenimiento |
| `POST` | `/api/v1/webhooks/mercadopago` | firma webhook | entrada de MercadoPago |

## notas de lectura

- Esta matriz describe el contrato tecnico, no el estado UX de cada modulo.
- Para estado de producto y caveats: `docs/product/estado-real-del-producto.md`.
