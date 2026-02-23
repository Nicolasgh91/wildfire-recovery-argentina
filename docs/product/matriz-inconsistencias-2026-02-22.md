# matriz de inconsistencias de documentacion (2026-02-22)

Objetivo: registrar diferencias entre claims existentes y estado real del producto para guiar la actualizacion documental.

## matriz claim -> fuente real -> accion

| claim detectado | fuente real (codigo/docs) | accion documental | prioridad |
|---|---|---|---|
| `README.md` apuntaba a `docs/use_cases.md` | el archivo no existe; se agrego `docs/casos de uso/casos_de_uso.md` | migrar al canónico `docs/product/casos-de-uso-y-estado.md` y dejar puente | P0 |
| roadmap con `68%` y UC-F11 pendiente | `frontend/src/pages/Exploration.tsx`, `app/api/v1/explorations.py`, workers activos | reemplazar porcentaje por estado real en semaforo | P0 |
| `/reports/judicial` figuraba publico en README | `docs/backend/api/auth_matrix.md` + router con JWT | alinear auth en README y docs canónicos | P0 |
| narrativa principal centrada en auditoria legal | rutas y UX actuales: `/exploracion`, `/map`, `/fires/history` | reposicionar a exploracion guiada y evidencia | P0 |
| `ForestGuard` como nombre principal en docs clave | `frontend/src/config/brand.ts` y `app/core/brand.py` usan Vestigia | unificar branding documental a Vestigia | P0 |
| MercadoPago presentado como completamente cerrado | flujos implementados con caveats (`PaymentReturnPage`, pricing, mock mode) | marcar como implementado con caveats/beta | P0 |
| docs de frontend mezclaban live y mock sin claridad | `CitizenReport.tsx` y `Certificates.tsx` usan mock; otras rutas live | explicitar estado por ruta y feature flags | P0 |
| documentos historicos se leian como vigentes | roadmaps y planes de ejecucion cerrados en `docs/architecture/*` y `docs/project/*` | mover a `docs/archive/2026-02/` + puente | P0 |
| estado de assets decia PDF separado/no integrado | `app/workers/exploration_hd_worker.py` + `workers/tasks/pdf_generation_task.py` | actualizar snapshot de assets al flujo real | P1 |
| onboarding tecnico largo para deploy | `scripts/deploy.sh`, workflows CI/CD actuales | simplificar entrada y mantener detalle avanzado | P1 |

## criterios de cierre de la auditoria

- README y docs canónicos cuentan la misma historia
- casos de uso y estado en una sola fuente
- semaforo de estado real visible para usuarios no tecnicos
- claims de diferenciacion respaldados por fuentes externas citadas
- documentacion historica separada sin romper navegacion
