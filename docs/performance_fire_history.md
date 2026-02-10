## Plan de performance - Grilla `/fires/history`

### 1. Evitar refetch al navegar
- [x] `keepPreviousData: true` en `useFires` y `useFireStats` para conservar resultados al cambiar de página o volver.
- [x] `staleTime = 5 min`, `cacheTime = 30 min` para reusar datos al regresar sin refetch inmediato.
- [x] Prefetch de la página siguiente al terminar de cargar la actual (o en `onMouseEnter` de los botones).

### 2. Reducir payload y render de la grilla
- [x] Virtualizar tabla desktop (scroll vertical con padding y slice de filas visibles, 48px + overscan).
- [x] Limitar columnas en mobile y opcionalmente en desktop detrás de un toggle; menos nodos a pintar.
- [x] `select` en la query para mapear a un DTO mínimo antes de llegar al componente (derivar `tableRows` con campos usados).
- [x] Extraer `<FireRow>` y envolver en `React.memo`; pasar solo props primitivos.

### 3. Paginación desktop
- [x] `page_size` inicial = 20. Al finalizar la carga de la página 1, disparar prefetch de la página 2 (otras 20). Cada vez que termina una página, se prefetchea la siguiente.
- [x] Prefetch en frontend (React Query): evita roundtrip al volver, controla cuándo hidratar la UI y reutiliza los filtros aplicados. El backend sigue paginando (`page`/`page_size`); el front solo decide cuándo pedir la próxima.

### 4. Paginación mobile (sin “cargando” global)
- [x] Mantener `page_size` = 20. No mostrar overlay de carga; la lista previa queda visible mientras llega la siguiente.
- [x] Spinner pequeño dentro de la lista mientras `isFetching` con datos previos.

### 5. Requests y caché de stats/export (detalle)
- [x] Unificar keys de React Query para `useFireStats` y los gráficos (usa el mismo hook/data); mismo `staleTime/cacheTime` y `structuralSharing`.
- [x] No refetchear si los filtros no cambian: filtros memorizados y hashing de queryKey evita refetch.
- [x] Export CSV ya es mutación separada y no invalida lista/estadísticas.

### 6. Coste de gráficos
- [x] `useMemo` para `provincesChartData`, `topFrpData`, `monthlyChartData` con dependencia única `statsPayload`.
- [x] `ResponsiveContainer` con alturas fijas (`h-56` mobile, `h-72` desktop), `barSize` moderado y truncado de labels para evitar desbordes.

### 7. Medición
- [x] Plan de medición:
  - React Query Devtools (prod build deshabilitado): revisar `cacheTime/staleTime` hits en la vista /fires/history tras navegación adelante/atrás.
  - React Profiler en modo dev sobre `FireHistoryPage` para medir commit time de la tabla virtualizada vs. carga inicial.
  - Lighthouse (desktop y mobile) sin header de QA: guardar reporte antes/después y comparar CLS, TTI, LCP.
- [ ] Ejecutar mediciones y adjuntar capturas/resultados al cerrar el trabajo.

### Paso 3 (¿cómo virtualizar?)
- [ ] `rowVirtualizer = useVirtualizer({ count: totalRows, estimateSize: 48, overscan: 8 })` sobre el contenedor de filas.
- [ ] Renderizar solo `virtualItems`, aplicando `paddingTop/paddingBottom` para conservar la altura total.
- [ ] Se mantiene la paginación del backend; la virtualización actúa solo sobre la página cargada.

Notas: Mantener compatibilidad con filtros actuales y backend `/api/v1/fires` / `/api/v1/fires/stats`; sin cambios de API.
