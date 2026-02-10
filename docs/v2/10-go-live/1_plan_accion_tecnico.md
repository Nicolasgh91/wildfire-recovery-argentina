# Plan de Acción Técnico para Completar Casos de Uso (Go-Live)

Este documento detalla las tareas técnicas necesarias para llevar cada caso de uso desde su estado actual hasta "Completado" (Verde), basándose en el análisis de `docs/v2/10-go-live/0_matriz_cobertura.md`.

---

## UC-F01: Contacto y Soporte
**Estado Actual:** Verde (Backend/Frontend OK), Amarillo (Workers/DB).

### Tareas Técnicas
1.  **Backend/Workers (Resiliencia):**
    - [ ] Implementar tarea asíncrona en Celery para el envío de correos SMTP. Desacoplar el envío del request HTTP para evitar timeouts y permitir reintentos automáticos.
    - [ ] Configurar política de reintentos (backoff exponencial) en caso de fallo del servidor SMTP.
2.  **Base de Datos (Auditoría):**
    - [ ] Implementar registro de logs estructurados para cada intento de contacto (éxito/fallo), sin guardar el contenido sensible del mensaje si no es necesario, pero sí metadatos (email remitente, timestamp, motivo de fallo).
3.  **Seguridad:**
    - [ ] Verificar y ajustar Rate Limiting en el endpoint `POST /api/v1/contact`.
    - [ ] Implementar validación estricta de tipos MIME y tamaño de archivos adjuntos antes de procesarlos.
4.  **Testing:**
    - [ ] Unit Test: Validaciones de input y adjuntos.
    - [ ] Integration Test: Flujo completo con mock de SMTP (simular éxito y caída de servicio).

---

## UC-F02: Estadísticas Públicas Agregadas
**Estado Actual:** Amarillo (Falta UI pública final, Cache, RLS).

### Tareas Técnicas
1.  **Frontend:**
    - [ ] Finalizar integración de la UI con endpoints públicos. Asegurar que las llamadas se realicen sin token de autenticación de usuario final.
2.  **Backend/Edge:**
    - [ ] Validar funcionamiento de Edge Function / RPC `public-stats`.
    - [ ] Implementar caché con TTL en el nivel de API o Edge para evitar consultas pesadas frecuentes a la DB.
3.  **Base de Datos & Seguridad:**
    - [ ] Configurar **RLS (Row Level Security)** en Supabase para permitir acceso `SELECT` a tablas/vistas de estadísticas solo al rol `anon` o service role específico, denegando todo lo demás.
4.  **Workers:**
    - [ ] Crear Cron Job diario para refrescar vistas materializadas o tablas de agregación si las estadísticas son pesadas (`REFRESH MATERIALIZED VIEW CONCURRENTLY`).
5.  **Testing:**
    - [ ] E2E: Verificar que un usuario no autenticado puede ver las estadísticas pero no acceder a datos crudos.
    - [ ] Performance: Test de carga en endpoints de estadísticas con rangos de tiempo amplios (>90 días).

---

## UC-F03: Histórico de Incendios y Dashboard
**Estado Actual:** Amarillo (Mayoría Verde, foco en consistencia y performance).

### Tareas Técnicas
1.  **Frontend (UX/Performance):**
    - [ ] Optimizar paginación en vista móvil (limitar page size a 50 ítems).
    - [ ] Verificar consistencia visual de filtros aplicados vs. datos mostrados en la grilla y KPIs.
2.  **Backend:**
    - [ ] Revisar índices de base de datos para consultas de filtrado por múltiples columnas (fecha, estado, severidad).
3.  **Testing:**
    - [ ] Integración: Asegurar que la exportación (`/fires/export`) respeta exactamente los filtros aplicados en el dashboard.
    - [ ] E2E: Navegación fluida Dashboard -> Detalle -> Volver (manteniendo estado/filtros).

---

## UC-F04: Calidad y Confiabilidad del Dato
**Estado Actual:** Verde/Amarillo (Falta exponer score en UI).

### Tareas Técnicas
1.  **Frontend:**
    - [ ] Implementar componente visual de "Score de Calidad" en la vista de detalle de incendio (`/fires/:id`). Mostrar advertencias si la metadata es incompleta (data source reliability).
2.  **Workers:**
    - [ ] Implementar trigger o job periódico que recalcule métricas de calidad si se ingesta nueva info (corrección de datos).
3.  **Testing:**
    - [ ] Unit Test: Validar algoritmo de cálculo de score ante datos faltantes.
    - [ ] Integración: Verificar degradación correcta del score en escenarios de prueba.

---

## UC-F05: KPIs de Recurrencia y Tendencias
**Estado Actual:** Amarillo (Dependencia UI y optimización DB).

### Tareas Técnicas
1.  **Frontend:**
    - [ ] Desarrollar componentes de visualización para mapas de calor (recurrencia) y gráficos de series temporales (tendencias).
2.  **Base de Datos (Optimización):**
    - [ ] Analizar plan de ejecución de consultas espaciales sobre `h3_recurrence_stats`. Añadir índices GiST/SP-GiST si es necesario.
3.  **Backend:**
    - [ ] Implementar validación estricta de Bounding Box (bbox) para evitar consultas excesivamente grandes que saturen la DB. Devolver 400 si el área es muy grande.
4.  **Worker:**
    - [ ] (Opcional MVP) Pre-calcular estadísticas mensuales para agregaciones rápidas.

---

## UC-F06: Auditoría Legal de Uso del Suelo
**Estado Actual:** Verde (Falta thumbnails).

### Tareas Técnicas
1.  **Storage / Workers:**
    - [ ] Implementar generación automática de thumbnails para evidencias visuales subidas/asociadas.
    - [ ] Almacenar thumbnails en bucket público (o firmado) optimizado para web.
2.  **Testing:**
    - [ ] Integración: Validar lógica de intersección con áreas protegidas (casos borde: incendio justo en el límite).
    - [ ] Seguridad: Validar restricción de API Key y Rate Limits (10 req/min).

---

## UC-F08: Carrusel Satelital de Incendios Activos
**Estado Actual:** Amarillo (UI parcial, falta Job diario).

### Tareas Técnicas
1.  **Backend/Workers:**
    - [ ] **Prioridad Alta:** Implementar Job diario (Cron) que:
        1. Identifique incendios activos.
        2. Consulte API de GEE para obtener la mejor imagen reciente.
        3. Genere thumbnails optimizados.
        4. Actualice el campo `slides_data` en `fire_events`.
    - [ ] Optimizar llamadas a GEE para controlar costos (batch processing).
2.  **Frontend:**
    - [ ] Finalizar componente de Carrusel para consumir `slides_data`. Manejar estados de carga y "imagen no disponible".
3.  **Storage:**
    - [ ] Configurar ciclo de vida/retención de imágenes si aplica, o asegurar persistencia correcta en GCS.

---

## UC-F09: Reporte de Cierre Pre/Post Incendio
**Estado Actual:** Amarillo (Falta Job de detección y generación).

### Tareas Técnicas
1.  **Workers:**
    - [ ] Implementar Job de cierre:
        1. Detectar incendios marcados como extinguidos recientemente.
        2. Generar reporte comparativo (Pre vs Post incendio).
        3. Generar PDF/GeoTIFF y subir a GCS.
        4. Marcar flags `has_historic_report` / fecha de generación.
2.  **Backend:**
    - [ ] Exponer endpoints para descarga segura de reportes generados.
3.  **Frontend:**
    - [ ] UI para visualizar disponibilidad del reporte y botón de descarga.
4.  **Infrastructure:**
    - [ ] Configurar reglas de retención en GCS: PDFs (90 días), GeoTIFF (7 días) para optimizar costos de almacenamiento.

---

## UC-F11: Reportes Especializados (Judicial + Históricos)
**Estado Actual:** Amarillo (Async Jobs y Colas).

### Tareas Técnicas
1.  **Backend/Workers:**
    - [ ] Separar colas de Celery: Crear cola específica `reports_queue` para no bloquear tareas rápidas (emails, notificaciones) con generación pesada de reportes.
    - [ ] Implementar `idempotency_key` en endpoints de solicitud de reporte para evitar duplicados ante reintentos del cliente.
2.  **Frontend:**
    - [ ] Implementar polling o websocket (si aplica) para notificar al usuario cuando el reporte asíncrono esté listo.
3.  **Testing:**
    - [ ] Validar generación de reportes parciales (ej. falta datos de clima) con disclaimers adecuados en el PDF final.

---

## UC-F13: Agrupación Macro y Gestión de Imágenes
**Estado Actual:** Amarillo.

### Tareas Técnicas
1.  **Backend/Logic:**
    - [ ] Refinar algoritmo de clustering para agrupación de eventos en episodios.
    - [ ] Asegurar trazabilidad N:M entre `fire_episodes` y `fire_events`.
2.  **Workers:**
    - [ ] Implementar job de mantenimiento de metadatos de imágenes (reproducibilidad).
3.  **Testing:**
    - [ ] Verificar reducción de requests a GEE gracias al agrupamiento (métricas).

---

## Tareas Transversales (Checklist Go-Live)
1.  **Infraestructura:**
    - [ ] Crear script de smoke test para verificar conectividad real con GCS (upload/read/delete) desde el entorno de producción.
    - [ ] Verificar configuración de variables de entorno para GEE y GCS en producción.
2.  **Observabilidad:**
    - [ ] Dashboards básicos de monitoreo (Logs de errores, latencia API, estado de Workers).
3.  **Documentación:**
    - [ ] Actualizar documentación de API con ejemplos de requests para reportes y auditoría.
