# SLOs - ForestGuard

## Objetivo
Definir objetivos de latencia y disponibilidad para los endpoints criticos de la plataforma.

## SLOs propuestos

| Servicio | Metrica | Objetivo | Fuente |
|----------|---------|----------|--------|
| `GET /api/v1/fires` | p95 latencia | < 500 ms | Metrics middleware |
| `GET /api/v1/fires/export` | p99 latencia | < 2 s | Metrics middleware |
| `POST /api/v1/audit/land-use` | p95 latencia | < 1 s | Metrics middleware |
| Endpoints publicos | Disponibilidad | 99.5% mensual | Health checks externos |
| Workers (reportes) | Completion rate | 95% en <1h | Celery / DLQ |
| GEE circuit breaker | Open state | < 5% del tiempo | Logs |

## Revision
- Revisar objetivos cada 90 dias o ante cambios mayores de infraestructura.
