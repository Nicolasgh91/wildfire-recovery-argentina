# Matriz de cobertura de casos de uso (UC-F01 a UC-F13)

> Propósito: mapear, para cada caso de uso, qué piezas existen (frontend, backend, workers, base de datos, storage), qué falta y qué probar en la prueba integral local previa a producción.

Leyenda:
- ✅ implementado / disponible
- 🟡 parcial / en progreso
- ⛔ pendiente / no implementado
- N/A no aplica al MVP

---

## Resumen ejecutivo (estado por UC)

> Nota: esta matriz es inventario tecnico por capa.
> Para estado de salida GO/NO GO prevalece `docs/v2/10-go-live/2_tech_go_live_tasks.md`.

| UC | Nombre | Frontend | Backend / Edge | Workers | DB | Storage | Estado actual |
|---|---|---:|---:|---:|---:|---:|---|
| UC-F01 | Contacto y soporte | ✅ (`/contact`) | ✅ (`POST /api/v1/contact`) | ✅ (cola SMTP) | ✅ (audit logs) | N/A | VERDE |
| UC-F02 | Estadísticas públicas agregadas | 🟡 (UI pública, depende de consumo) | 🟡 (Edge + RPC en repo) | ⛔ (cron réplica/refresh) | 🟡 (vista/RPC) | N/A | AMARILLO |
| UC-F03 | Histórico de incendios y dashboard | ✅ (`/fires`, `/fires/:id`) | ✅ (`/api/v1/fires*`) | N/A | ✅ | N/A | AMARILLO |
| UC-F04 | Calidad y confiabilidad del dato | 🟡 (ideal: panel en detalle) | ✅ (`/api/v1/quality/fire-event/{id}`) | 🟡 (refresh vista) | ✅ (MV/vista quality) | N/A | VERDE |
| UC-F05 | KPIs de recurrencia y tendencias | 🟡 (depende UI) | ✅ (`/api/v1/analysis/recurrence`, `/trends`) | 🟡 (precompute/cache) | 🟡 (MV h3_recurrence_stats) | N/A | AMARILLO |
| UC-F06 | Auditoría legal de uso del suelo | ✅ (`/audit`) | ✅ (`POST /api/v1/audit/land-use`) | N/A | ✅ | 🟡 (thumbnails evidencia) | VERDE |
| UC-F07 | Registro de visitantes offline | N/A | N/A | N/A | N/A | N/A | N/A (fuera del MVP) |
| UC-F08 | Carrusel satelital de incendios activos | 🟡 (UI consume `slides_data`) | 🟡 (servicios internos) | ⛔ (job diario) | 🟡 | ✅ (GCS thumbnails) | AMARILLO |
| UC-F09 | Reporte de cierre pre/post incendio | 🟡 (visualización/descarga) | 🟡 (job + flags) | ⛔ (job diario) | 🟡 | ✅ (GCS thumbnails + retención) | AMARILLO |
| UC-F10 | Certificación legal monetizada | ✅ (`/certificates`, UI existe) | 🟡 | 🟡 | 🟡 | 🟡 | N/A (fuera del MVP) |
| UC-F11 | Reportes especializados (judicial + históricos) | ✅ (`/exploration` wizard) | ✅ (`POST /api/v1/reports/judicial|historical`) | 🟡 (colas separadas) | 🟡 (tablas jobs/idempotency) | 🟡 (PDF+HD on-demand) | AMARILLO |
| UC-F12 | Recuperación y cambio de uso (VAE) | 🟡 (monitoring/reports) | 🟡 (servicio VAE en backend) | 🟡 | 🟡 | N/A | AMARILLO (fuera de MVP_CORE) |
| UC-F13 | Agrupación macro y gestión de imágenes reproducibles | 🟡 (impacta UI indirectamente) | 🟡 (servicios internos) | ⛔ (macro clustering + metadata) | 🟡 (episodios N:M) | ✅ (GCS thumbnails) | AMARILLO |

---

## Matriz detallada por caso de uso

### UC-F01 — Contacto y soporte
| Capa | Cobertura | Detalle |
|---|---|---|
| Frontend | ✅ | Ruta `/contact` (formulario) |
| Backend | ✅ | `POST /api/v1/contact` operativo (validaciones + 202) |
| Workers | ✅ | Envío asíncrono con Celery (`send_contact_email`) y reintentos |
| DB | ✅ | Logs de auditoría estructurados (`AUDIT: ...`) |
| Storage | N/A | No se deben persistir adjuntos (procesamiento en memoria) |
| Seguridad | ✅ | Rate limit activo + validación estricta de adjuntos |

Pruebas clave:
- Unit: validación de tipos/tamaño de archivo.
- Integración: SMTP OK / SMTP caído (reintentos si hay cola).
- Seguridad: rate limit y payloads maliciosos.

---

### UC-F02 — Estadísticas públicas agregadas
| Capa | Cobertura | Detalle |
|---|---|---|
| Frontend | 🟡 | Página pública existe como concepto (no debe usar endpoints auth) |
| Edge / RPC | 🟡 | `GET /functions/v1/public-stats` + RPC en repo (`supabase/functions/public-stats`) |
| Workers / Cron | ⛔ | Cron diario para réplica/refresh + cache TTL |
| DB | 🟡 | RPC y vista existen en entorno de codigo/tests |
| Seguridad | 🟡 | Falta validacion en entorno Supabase objetivo (RLS + anon) |

Pruebas clave:
- E2E: usuario anónimo no puede leer tablas/vistas directas.
- Performance: rangos <=90 días (diario) y >90 (mensual).
- Resiliencia: cache hit/miss y rate limit 429.

---

### UC-F03 — Histórico de incendios y dashboard
| Capa | Cobertura | Detalle |
|---|---|---|
| Frontend | ✅ | `/fires` (dashboard) + `/fires/:id` (detalle) |
| Backend | ✅ | `GET /api/v1/fires`, `/fires/stats`, `/fires/export` |
| DB | ✅ | `fire_events`, vistas `fire_stats`, `fire_event_quality_metrics`, joins varios |
| Seguridad | ✅ | Ruta protegida (auth) + paginación server-side |

Pruebas clave:
- Integración: consistencia de filtros (grilla/KPIs/export).
- E2E: navegación `/fires` → detalle → export.
- Performance: índices y paginación (page_size mobile max 50).

---

### UC-F04 — Calidad y confiabilidad del dato
| Capa | Cobertura | Detalle |
|---|---|---|
| Frontend | 🟡 | Ideal: mostrar score/limitaciones dentro de `/fires/:id` |
| Backend | ✅ | `GET /api/v1/quality/fire-event/{fire_event_id}` |
| DB | ✅ | MV/vista `fire_event_quality_metrics` + `data_source_metadata` |
| Workers | 🟡 | Refresh por cron o al actualizar eventos (según estrategia) |

Pruebas clave:
- Unit: fórmula del score (versionada).
- Integración: metadata incompleta → score degradado + warnings.
- Performance: respuesta <1s para casos comunes.

---

### UC-F05 — KPIs de recurrencia y tendencias
| Capa | Cobertura | Detalle |
|---|---|---|
| Frontend | 🟡 | Depende de UI (mapas/series) |
| Backend | ✅ | `GET /api/v1/analysis/recurrence`, `GET /api/v1/analysis/trends` |
| DB | 🟡 | MV `h3_recurrence_stats` + geoconsultas; requiere índices y límites |
| Workers | 🟡 | Precompute/cache recomendado para rangos comunes |

Pruebas clave:
- Validación: bbox demasiado grande → 400.
- Performance: rangos comunes <2s.
- Correctitud: reglas low/medium/high y agregación mensual >90 días.

---

### UC-F06 — Auditoría legal de uso del suelo
| Capa | Cobertura | Detalle |
|---|---|---|
| Frontend | ✅ | `/audit` (flujo guiado) |
| Backend | ✅ | `POST /api/v1/audit/land-use` |
| DB | ✅ | `land_use_audits`, `fire_events`, `protected_areas`, intersecciones |
| Storage | 🟡 | Evidencia visual: thumbnails si existen |
| Seguridad | ✅ | API key obligatoria + rate limit |

Pruebas clave:
- Integración: casos sin incendios (is_prohibited=false).
- Geoespacial: radios, bordes, geometrías raras.
- Seguridad: rate limit 10 req/min, API key requerida.

---

### UC-F07 — Registro de visitantes offline
Fuera del MVP. No se incluye en el plan de prueba integral.

---

### UC-F08 — Carrusel satelital de incendios activos
| Capa | Cobertura | Detalle |
|---|---|---|
| Frontend | 🟡 | UI puede renderizar carrusel si `fire_events.slides_data` está poblado |
| Backend | 🟡 | Servicios internos (GEEService + StorageService) |
| Workers | ⛔ | Job diario: best image + thumbnails + update `slides_data` |
| DB | 🟡 | `fire_events.slides_data`, `fire_imagery/satellite_images` |
| Storage | ✅ | Thumbnails persistentes en GCS |

Pruebas clave:
- Worker: no regenerar si `last_gee_image_id` no cambia.
- Costos: batch size (15) + rate limit GEE.
- UI: carrusel no muestra ítems sin `thumbnail_url`.

---

### UC-F09 — Reporte de cierre pre/post incendio
| Capa | Cobertura | Detalle |
|---|---|---|
| Frontend | 🟡 | Vista/descarga del before/after (según implementación) |
| Backend | 🟡 | Flags: `has_historic_report`, reglas de retención |
| Workers | ⛔ | Job detecta extinguidos + genera pre/post + marca flag |
| DB | 🟡 | `fire_events.extinguished_at`, `has_historic_report` |
| Storage | ✅ | Thumbnails indefinidos; PDFs 90 días; GeoTIFF 7 días |

Pruebas clave:
- Idempotencia por flag: corre 2 veces → no duplica.
- Fallback pre-incendio (-30) y reintento post-incendio.
- Retención automática (limpieza).

---

### UC-F10 — Certificación legal monetizada
Fuera del MVP, pero hay UI activa (`/certificates`). Si se mantiene visible:
- Asegurar que no exponga endpoints que no existan o que impliquen riesgos/costos.
- Gatear por feature flag o “coming soon” para evitar confusión/abuso.

---

### UC-F11 — Reportes especializados (judicial + históricos)
| Capa | Cobertura | Detalle |
|---|---|---|
| Frontend | ✅ | `/exploration` (wizard) + compra créditos/pago |
| Backend | ✅ | `POST /api/v1/reports/judicial`, `POST /api/v1/reports/historical` |
| Workers | 🟡 | Jobs asíncronos; ideal: colas separadas para no bloquear |
| DB | 🟡 | `idempotency_keys` + `historical_report_requests` (y estados de job) |
| Storage | 🟡 | PDF en GCS; HD on-demand (sin persistencia) |
| Seguridad | 🟡 | Idempotency obligatoria + control de acceso + rate limit |

Pruebas clave:
- Idempotency: reintento POST → no duplica.
- Estado consultable del job (queued/running/done/error).
- Parciales: sin clima → disclaimer y continúa.

---

### UC-F12 — Recuperación y cambio de uso (VAE)
Implementacion parcial en backend (servicio y endpoints de monitoreo), fuera del perfil `MVP_CORE`.

---

### UC-F13 — Agrupación macro y gestión de imágenes reproducibles
| Capa | Cobertura | Detalle |
|---|---|---|
| Frontend | 🟡 | Impacta indirectamente: mejores episodios + thumbnails consistentes |
| Backend | 🟡 | Servicios de clustering + metadata reproducible (recetas) |
| Workers | ⛔ | Job de clustering macro + job de imagery metadata |
| DB | 🟡 | `fire_episodes`, `fire_episode_events` (N:M), `gee_system_index`, `bands_config` |
| Storage | ✅ | Thumbnails persistentes; HD siempre on-demand |

Pruebas clave:
- Correctitud: N:M episodio-evento trazable.
- Reducción de requests GEE (métrica comparativa).
- Validación: episodios sin imagen → marcado consistente (sin romper UI).

---

## Checklist de prueba integral local (para “go/no-go”)

1) Health checks (API, DB, Celery, GEE).
2) Conectividad real a GCS (script de test: upload/read/delete en buckets).
3) Ejecutar al menos 1 corrida de worker de thumbnails (o simular) y verificar:
   - `fire_events.slides_data` poblado
   - objetos en GCS accesibles
4) UI:
   - home / carruseles no muestran tarjetas sin `thumbnail_url`
   - `/fires` filtros + KPIs + export coherentes
   - `/audit` responde y loguea auditoría
5) Reportes (si se habilitan en local):
   - creación de job asíncrono + idempotencia
   - PDF en GCS y retención (si aplica)

---
