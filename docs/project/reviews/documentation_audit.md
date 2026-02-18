# Documentation Audit (MVP publicable)

## Mapa de fuentes (estado canónico usado)

Dado que no existen archivos con nombre exacto `sistema_overview`, `api_documentation`, `project_roadmap`, `infrastructure_documentation`, `gcs_remediation_tasks`, `gcs_connectivity_diagnostic`, `user_manual_es`, se usaron como fuentes canónicas operativas:

1. `README.md` (visión general, setup, API reference)
2. `frontend/README.md` (rutas UI + contratos frontend/backend)
3. `docs/architecture/roadmap_prod.md` (estado MVP/post-MVP y roadmap)
4. `docs/architecture/technical_tasks_roadmap.md` (nomenclatura vigente Audit -> Verificar terreno, Certificates -> Exploración)
5. `docs/architecture/frontend/0_frontend_roadmap.md` (integración frontend y decisiones técnicas)
6. `docs/architecture/workers_documentation.md` (inventario de workers)

Referencias canónicas clave respetadas:
- Renombre de UX en `docs/architecture/technical_tasks_roadmap.md` (sección "Resumen de cambios" y T7.1).
- Estado general de fases en `docs/architecture/roadmap_prod.md`.

## Inconsistencias detectadas y estado

| archivo | sección | problema | fix aplicado | pendiente |
|---|---|---|---|---|
| `README.md` | Instalación / env | Indicaba `cp .env.example .env` pero el repo usa `.env.template` | Actualizado a `.env.template` | No |
| `README.md` | Instalación manual | Ruta frontend decía `cd ../frontend` (inconsistente desde raíz) | Corregido a `cd frontend` | No |
| `README.md` | API Reference | Auth de `/fires` y `/fires/{id}` documentada como API key, pero son públicos | Tabla corregida a Público | No |
| `README.md` | API Reference | Auth de `/audit/land-use` documentada como API key, pero requiere JWT | Tabla y ejemplo curl actualizados a Bearer JWT | No |
| `frontend/README.md` | Routing | Naming legacy (`Audit`, `Reports`) sin alinear al flujo actual `/exploracion` | Rutas alineadas (`/audit` como Verificar terreno, `/reports` alias legacy) | No |
| `frontend/README.md` | Routing | No se explicitaba auth requerida para rutas protegidas | Se agregó nota en `/audit` y `/fires/history` | No |
| `frontend/README.md` | Routing | No se explicitaban feature flags en `/certificates` y `/shelters` | Se documentaron flags `certificates` y `refuges` | No |
| `frontend/README.md` | API contracts | Contrato de exploración disperso bajo reports | Se separó `/exploracion` (live) + `/reports` (alias/helpers) | No |
| `README.md` | API Reference | `/reports/judicial` aparece público en código actual, potencialmente no deseado | Se dejó documentado como "Público (MVP actual)" para reflejar estado real | Sí: endurecer auth backend |
| `docs/*` | Fuentes canónicas solicitadas por nombre | Los nombres pedidos no existen literalmente en el repo | Se dejó trazabilidad explícita de mapeo de fuentes en este documento | Sí: consolidar naming canónico único |

## Ítems de auditoría (formato estándar)

### ID: DOC-001
**Severidad:** media  
**Área:** docs  
**Evidencia:** `README.md` (setup y API Reference)  
**Riesgo:** Setup y auth desalineados con el código generan onboarding incorrecto y pruebas falsas (ej. usar API key donde requiere JWT).  
**Recomendación:** Mantener `README.md` como documento de entrada y validar auth/rutas contra código en cada release.  
**Estado:** resuelto

### ID: DOC-002
**Severidad:** media  
**Área:** docs/frontend  
**Evidencia:** `frontend/README.md` (routing y contratos API por página)  
**Riesgo:** Naming legacy (`reports`, `audit`, `certificates`) sin aclaraciones induce expectativas erróneas sobre UX y disponibilidad de features.  
**Recomendación:** Conservar sección de alias legacy (`/reports`) y marcar claramente flags/estados MVP.  
**Estado:** resuelto

### ID: DOC-003
**Severidad:** baja  
**Área:** docs  
**Evidencia:** `docs/architecture/roadmap_prod.md` vs `docs/architecture/technical_tasks_roadmap.md`  
**Riesgo:** Múltiples fuentes de estado pueden divergir y degradar decisiones de producto/infra.  
**Recomendación:** Definir un único índice maestro de documentación canónica con fecha de vigencia.  
**Estado:** pendiente

### ID: DOC-004
**Severidad:** baja  
**Área:** docs  
**Evidencia:** ausencia de nombres exactos solicitados (`sistema_overview`, `api_documentation`, etc.) en árbol `docs/`  
**Riesgo:** Auditorías futuras pierden trazabilidad al no encontrar por nombre la fuente de verdad esperada.  
**Recomendación:** Crear alias/índice o renombrar documentos para converger con nomenclatura canónica definida por el equipo.  
**Estado:** pendiente

## Cambios aplicados en esta ejecución

- `README.md` actualizado para coherencia de setup y auth real.
- `frontend/README.md` actualizado para naming UX vigente y rutas/feature flags reales.

## Observaciones

- Persisten documentos históricos con estados cerrados/abiertos no siempre consistentes entre sí (`roadmap_prod` vs `technical_tasks_roadmap`).
- Recomendado consolidar una única "fuente de verdad" para estado MVP y nomenclatura de producto.
