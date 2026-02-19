# ForestGuard — Auth Matrix (BL-012)

Endpoint authentication requirements. Generated from `tests/unit/test_auth_matrix.py`.

| Method | Endpoint | Auth | Notes |
|--------|----------|------|-------|
| `POST` | `/api/v1/reports/judicial` | JWT | Forensic judicial report |
| `POST` | `/api/v1/reports/historical` | JWT | Historical fire report |
| `GET` | `/api/v1/reports/{id}/verify` | JWT | Report verification |
| `POST` | `/api/v1/explorations/` | JWT | Create exploration draft |
| `GET` | `/api/v1/explorations/` | JWT | List user explorations |
| `POST` | `/api/v1/audit/land-use` | JWT | Legal land-use audit |
| `GET` | `/api/v1/payments/credits/balance` | JWT | Credit balance |
| `GET` | `/api/v1/payments/credits/transactions` | JWT | Transaction history |
| `POST` | `/api/v1/payments/checkout` | JWT | Create checkout session |
| `GET` | `/api/v1/fires` | Public | List fire events |
| `GET` | `/api/v1/fires/{id}` | Public | Fire event detail |
| `GET` | `/api/v1/fires/stats` | API Key or JWT | Aggregated stats |
| `GET` | `/api/v1/fires/export` | API Key or JWT | Export dataset |
| `POST` | `/api/v1/contact` | Public | Contact form (rate limited) |
| `GET` | `/health` | Public | Health check |
| `GET` | `/api/v1/quality/fire-event/{id}` | API Key | Quality metrics |
| `GET` | `/api/v1/certificates/*` | API Key + Feature flag | Certificates (MVP off) |
| `*` | `/api/v1/alerts/*` | API Key | Park capacity alerts |
| `*` | `/api/v1/workers/*` | API Key | Worker endpoints (admin) |
| `*` | `/api/v1/tasks/*` | API Key | Maintenance tasks |
| `POST` | `/api/v1/webhooks/mercadopago` | Signature | MercadoPago webhook |

> **Validation**: Run `pytest tests/unit/test_auth_matrix.py -v` to verify contract.
> **Regenerate**: Run `python scripts/generate_auth_matrix.py` to update this file.
