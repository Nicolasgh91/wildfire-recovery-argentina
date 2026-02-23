# backlog de actualizacion documental (2026-02-22)

Estado: ejecutado en rama `docs_documentation_refresh_2026_02_22` y dejado en staging (sin commit).

## checklist de tareas

- [x] **P0**
  - archivo objetivo: `README.md`
  - problema detectado: narrativa mixta, links rotos, claims desactualizados
  - cambio propuesto: reposicionamiento a exploracion, estado real, limites honestos, links canónicos
  - criterio de aceptacion: comprension en <10 segundos y links locales validos
  - esfuerzo: L

- [x] **P0**
  - archivo objetivo: `docs/INDEX.md`
  - problema detectado: mezcla de canon e historico
  - cambio propuesto: separar canon vigente y archivo historico
  - criterio de aceptacion: navegacion clara hacia docs actuales
  - esfuerzo: M

- [x] **P0**
  - archivo objetivo: `docs/product/README.md`
  - problema detectado: no habia hub canonico
  - cambio propuesto: crear centro de docs de producto
  - criterio de aceptacion: enlazado desde README e INDEX
  - esfuerzo: S

- [x] **P0**
  - archivo objetivo: `docs/product/casos-de-uso-y-estado.md`
  - problema detectado: no habia fuente unica UC/estado
  - cambio propuesto: migrar y normalizar desde `docs/casos de uso/casos_de_uso.md`
  - criterio de aceptacion: tabla unica vigente + extracto en README
  - esfuerzo: M

- [x] **P0**
  - archivo objetivo: `docs/product/estado-real-del-producto.md`
  - problema detectado: estados dispersos e inconsistentes
  - cambio propuesto: semaforo ✅🟡⏳❌ + top 5 de cierre
  - criterio de aceptacion: estado real claro y trazable
  - esfuerzo: M

- [x] **P0**
  - archivo objetivo: `docs/frontend/README.md`
  - problema detectado: mezcla live/mock sin caveats
  - cambio propuesto: estado por ruta y caveats reales
  - criterio de aceptacion: consistente con `frontend/src/App.tsx` y paginas clave
  - esfuerzo: M

- [x] **P0**
  - archivo objetivo: `docs/backend/api/auth_matrix.md`
  - problema detectado: copy/naming legacy
  - cambio propuesto: mantener contrato factual y actualizar redaccion
  - criterio de aceptacion: sin contradiccion con README
  - esfuerzo: S

- [x] **P0**
  - archivo objetivo: `docs/infrastructure/deployment/DEPLOYMENT.md`, `docs/flujo-deploy.md`
  - problema detectado: runbook confuso para entrada
  - cambio propuesto: simplificar local/deploy actual y mantener referencias avanzadas
  - criterio de aceptacion: flujo reproducible y entendible
  - esfuerzo: M

- [x] **P0**
  - archivo objetivo: `docs/product/diferenciacion-mercado.md`
  - problema detectado: faltaba investigacion externa con citas
  - cambio propuesto: relevamiento con fuentes y claim prudente
  - criterio de aceptacion: incluye citas y fecha de consulta
  - esfuerzo: M

- [x] **P0**
  - archivo objetivo: `docs/archive/**` + rutas originales
  - problema detectado: documentos viejos se leian como vigentes
  - cambio propuesto: archivado en `docs/archive/2026-02/` + archivos puente
  - criterio de aceptacion: navegacion historica sin perder trazabilidad
  - esfuerzo: L

- [x] **P1**
  - archivo objetivo: `docs/assets-generation/status_2026-02-22.md`
  - problema detectado: snapshot parcialmente desactualizado
  - cambio propuesto: reflejar estado implementado actual de pipeline HD/PDF
  - criterio de aceptacion: coherencia con workers/servicios actuales
  - esfuerzo: M

- [x] **P2**
  - archivo objetivo: docs canónicos transversales
  - problema detectado: lenguaje legacy como narrativa principal
  - cambio propuesto: barrido final y reposicionamiento
  - criterio de aceptacion: legal queda como modulo avanzado
  - esfuerzo: S

## nota operativa

Se detecto una regla de `.gitignore` que excluye rutas con `architecture`.
Para incluir el archivado de esos documentos se uso `git add -f` de forma acotada.
