Plan de análisis AS-IS: UC-F12 VAE (+ conflicto de nomenclatura UC-12)
Resumen
Voy a entregar un informe técnico en español, centrado en cómo funciona hoy UC-F12 (VAE): cómo se generan datos, cómo se procesan, qué endpoints los exponen y qué se muestra en pantalla por página.
También incluiré una sección explícita de conflicto de nomenclatura (UC-12 vs UC-F12) y un gap analysis documentación vs código.

Alcance confirmado
UC-F12/UC-06 como foco principal (VAE).
Inclusión del conflicto de nomenclatura con UC-12 (Visitor Logs / histórico).
Formato de salida: as-is + gaps (no solo descripción).
Fuentes a consolidar (single source for this analysis)
Documentación VAE:
UC_F12_implementation_spec.md
UC_F12_critical_review.md
tech_plan_ef_12.md
casos-de-uso-y-estado.md
Backend runtime real:
monitoring.py
main.py
recovery.py
destruction.py
workers/celery_app.py
docker-compose.yml
2026_02_23_uc_f12_vae_monitoring.sql
Frontend visualización real:
App.tsx
FireDetail.tsx
RecoveryPanel.tsx
RecoveryStatusBadge.tsx
monitoring.ts
MapPage.tsx
Plan de ejecución (analítico)
Construir mapa de nomenclatura y alcance UC.
Tabla de equivalencias: UC-F12/UC-06 (monitoring VAE) vs UC-12 (visitor logs / histórico).
Marcar referencias ambiguas en docs/código.
Levantar flujo de datos backend extremo a extremo.
Generación: endpoint manual POST /monitoring/recovery/trigger, tareas y scheduling.
Procesamiento: VAEService y reglas de cálculo.
Persistencia: vegetation_monitoring y land_use_changes (+ constraints/RLS declarados en migración).
Exposición: GET /monitoring/recovery/{id}, GET /monitoring/land-use-changes/{id}, GET /monitoring/recovery/summary.
Levantar flujo frontend y pantallas.
Página por página: rutas donde hay consumo VAE y rutas donde no.
Render condicional por autenticación.
Componentes concretos y campos mostrados en UI.
Ejecutar gap analysis documentación vs implementación.
Estado de implementación de lo que docs declaran como “faltante”.
Desalineaciones funcionales críticas (colas, auth, taxonomías de estado, páginas realmente visibles).
Entregar informe final en formato operativo.
Secciones: AS-IS, Gaps, Riesgos, Matriz página->dato->endpoint, Matriz endpoint->tabla->worker.
APIs/interfaces/tipos públicos: tratamiento en este análisis
No se proponen cambios de código en esta fase (análisis-only).
Sí se documentarán contratos actuales efectivos:
Endpoints /api/v1/monitoring/*.
Tipos frontend RecoveryResponse, LandUseChangesResponse.
Estados de recuperación backend vs mapeo visual en badge.
Se señalarán desalineaciones de contrato observadas (sin mutar código).
Casos y escenarios de validación del análisis
Evento sin registros en vegetation_monitoring -> respuesta pending y qué muestra UI.
Evento con serie NDVI -> cómo aparece en RecoveryPanel y NdviChart.
Evento con land_use_changes + violaciones -> tarjetas y conteo de violaciones.
Usuario no autenticado en /fires/:id -> qué se ve y qué no se renderiza.
Trigger manual admin -> recorrido hasta cola y riesgo operativo por enrutamiento/consumo.
Mapa principal -> verificar si la señal de violación se alimenta hoy o queda solo capacidad visual.
Criterios de aceptación del entregable
Lista explícita de páginas donde VAE se muestra hoy, y qué elementos exactos ve el usuario en cada una.
Flujo técnico completo origen -> proceso -> persistencia -> API -> UI con archivos fuente.
Matriz de brechas docs vs código con severidad (alto/medio/bajo) y evidencia.
Sección de nomenclatura que elimine ambigüedad entre UC-12 y UC-F12.
Supuestos y defaults elegidos
Se trabaja sobre snapshot local actual del repositorio.
El análisis es estático (código/docs/config), sin dependencia de datos productivos en vivo.
Lenguaje del informe: español técnico.
Alcance congelado a VAE + conflicto de nomenclatura, sin extender a implementación en este turno.