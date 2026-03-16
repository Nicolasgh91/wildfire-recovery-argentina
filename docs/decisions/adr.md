# Registro de decisiones arquitectónicas

Este archivo actúa como índice de decisiones arquitectónicas relevantes para el sistema.

## ADRs

- `docs/decisions/ADR-0001-auth-supabase.md`  
  - **Título**: Autenticación única con Supabase Auth  
  - **Fecha**: 2026-02-12  
  - **Estado**: Accepted  
  - **Resumen**: Se unifica la autenticación en Supabase Auth, eliminando el sistema de auth nativo y alineando frontend y backend en torno a un único proveedor de identidad.

- `docs/decisions/ADR-0002-baseline-ndvi-quality-mosaic.md`  
  - **Título**: Baseline NDVI por composite de máximo NDVI (quality mosaic)  
  - **Fecha**: 2026-03-15  
  - **Estado**: Accepted  
  - **Resumen**: El baseline NDVI se calcula como pico de vegetación anual (quality mosaic sobre 12/24 meses pre-incendio) en lugar de una sola imagen en ventana 45–15 días.

- `docs/decisions/ADR-0003-return-context-audit.md`  
  - **Título**: Origen `audit` en ReturnContext y límites de datos en sessionStorage  
  - **Fecha**: 2026-03-16  
  - **Estado**: Accepted  
  - **Resumen**: Se incorpora un nuevo origen `returnTo: 'audit'` al `ReturnContext` del frontend para UC-F06. Solo se persisten en `sessionStorage` parámetros compactos (`lat`, `lon`, `radius`, `page`) necesarios para reconstruir la búsqueda en auditoría, sin guardar resultados ni textos completos de auditoría en cumplimiento con la ley 25.326.

Nuevas decisiones deben documentarse como archivos adicionales en esta carpeta y enlazarse desde este índice.
