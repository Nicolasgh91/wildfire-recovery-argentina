# estado real del producto

Fecha de corte: 22 de febrero de 2026.

## semaforo de estado

### ✅ listo en produccion

- Exploracion satelital guiada (`/exploracion`) con gestion de borradores, items y generacion.
- Generacion de assets HD con tracking y polling de estado.
- Generacion y descarga de PDF en flujo de exploracion/reportes.
- Historico de incendios con filtros, estadisticas y export.
- Mapa de incendios con datos reales de episodios.
- Verificar terreno como modulo avanzado con autenticacion.
- Contacto y soporte publico.
- Pipeline tecnico de ingestion, clustering y carrusel operativo.

### 🟡 implementado con caveats

- MercadoPago: checkout y retorno implementados, con caveats operativos de validacion de estado y dependencias de entorno.
- Certificados: backend disponible bajo restricciones; frontend aun en modo mock y feature flag.
- Citizen report: UX disponible, envio final todavia simulado en frontend.
- Shelters/visitor logs: funcionalidades implementadas con feature flag (no expuestas por defecto).
- Calidad/recurrencia: endpoints y base tecnica presentes, cobertura UX aun parcial.

### ⏳ en progreso

- Producto de recuperacion/cambio de uso (VAE) como experiencia consolidada de usuario.
- Consolidacion final de copy y microcopy en toda la documentacion y UI.
- endurecimiento final de observabilidad operativa de pagos/reportes.

### ❌ descartado o post-MVP

- Narrativa principal de "auditoria legal" como posicionamiento central del producto.
- Cualquier promesa de certificacion legal masiva como feature principal de entrada.

## que puede hacer una persona usuaria hoy

1. Explorar incendios historicos y recientes en mapa e historial.
2. Armar una investigacion guiada con fechas pre/post y generar evidencia HD.
3. Descargar reporte en PDF para compartir o documentar hallazgos.
4. Verificar un terreno cuando necesita un analisis con componente legal.
5. Comprar creditos para flujos de evidencia ampliada (con caveats operativos).

## top 5 para cierre producto/UX

1. Completar el paso de citizen report para pasar de mock a envio real end-to-end.
2. Cerrar el frente de certificados (definir si se activa, reescribe o se mueve a modulo institucional).
3. Reducir friccion en pagos/retorno (mensajes, fallback, trazabilidad de estados).
4. Unificar microcopy de exploracion/verificar terreno/manual para usuario no tecnico.
5. Publicar metricas operativas de confiabilidad (tiempos, tasa de exito de reportes y assets).

## notas de exactitud

Este estado se valida contra rutas y codigo activos en:

- `frontend/src/App.tsx`
- `frontend/src/pages/Exploration.tsx`
- `app/api/v1/explorations.py`
- `app/api/routes/reports.py`
- `app/api/v1/payments.py`
- `docs/backend/api/auth_matrix.md`
