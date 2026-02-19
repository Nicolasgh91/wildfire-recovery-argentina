# Frontend Technical Debt

## TD-FE-001: Oversized bundle chunk warning
- **Timestamp**: 2026-02-19T14:33:08-03:00
- **Task ID**: TSK-04
- **Log/Error observado**: Vite build warning: `Some chunks are larger than 500 kB after minification` (`assets/index-*.js` reported at ~655 kB).
- **Hipotesis de la causa**: Main chunk still aggregates multiple route-level dependencies despite manual chunk settings.
- **Workaround aplicado**: None (non-blocking warning, build succeeds).
- **Propuesta de fix**: Increase route-level code-splitting and revisit `manualChunks` to force stable feature chunks for heavy views.
- **Prioridad**: Medium

## TD-FE-002: Dynamic import does not split due static imports
- **Timestamp**: 2026-02-19T14:33:08-03:00
- **Task ID**: TSK-04
- **Log/Error observado**:
  - `fire-card.tsx is dynamically imported ... but also statically imported`
  - `supabase.ts is dynamically imported ... but also statically imported`
- **Hipotesis de la causa**: Modules are referenced both by static and dynamic import paths, preventing Rollup from moving them into dedicated async chunks.
- **Workaround aplicado**: None (non-blocking warning, functionality unaffected).
- **Propuesta de fix**: Consolidate imports to a single loading strategy per module (either static or lazy) and re-run bundle analysis.
- **Prioridad**: Low
