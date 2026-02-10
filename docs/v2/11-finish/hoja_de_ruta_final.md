# Hoja de ruta final: ForestGuard go-live

**Generado**: 2026-02-10  
**Basado en**: Análisis de 16 archivos de documentación del proyecto

---

## 1. Resumen ejecutivo

### Estado general
- **Perfil recomendado**: `MVP_CORE` (con habilitación opcional de `ASYNC_GCS`)
- **Bloqueantes críticos**: 2
- **Inconsistencias detectadas**: 4
- **Tareas técnicas pendientes**: 12

### Decisión GO/NO-GO
| Perfil | Estado | Condición |
|--------|--------|-----------|
| MVP_CORE | **GO condicional** | Resolver bloqueantes críticos |
| ASYNC_GCS | **GO condicional** | MVP_CORE + evidencia funcional de workers |

---

## 2. Inconsistencias detectadas entre documentos

### 2.1 Estado de UC-F02 (estadísticas públicas)
| Documento | Estado reportado |
|-----------|-----------------|
| `0_matriz_cobertura.md` | AMARILLO |
| `2_tech_go_live_tasks.md` | VERDE |
| `go_live_status.md` | COMPLETADO (14/14 checks) |

**Resolución**: El estado correcto es **VERDE**. La matriz debe actualizarse para reflejar la validación del 2026-02-10 documentada en `go_live_status.md`.

### 2.2 Nomenclatura auditoría vs. verificar terreno
| Archivo | Terminología |
|---------|--------------|
| `0_matriz_cobertura.md` | "Auditoría legal de uso del suelo" |
| `razones_redisenio_verificar_terreno.md` | "Verificar terreno" |
| `old_audit_new_verify_land_tech_tasks.md` | Define cambio a "Verificar terreno" |

**Resolución**: Verificar que el frontend implementó el cambio de nomenclatura. La matriz debe reflejar el nuevo nombre "Verificar terreno (UC-F06)".

### 2.3 Workers pendientes: job diario vs. bajo demanda
| UC | Documento técnico | Documento de rediseño |
|----|-------------------|----------------------|
| UC-F08 | Job diario de refresh | No especifica frecuencia |
| UC-F09 | Job detecta extinguidos | Menciona "auto-generación solo significativos" |
| UC-F13 | Job de clustering macro | No hay documento de rediseño asociado |

**Resolución**: Confirmar si los workers están configurados como cron jobs o requieren trigger manual. Documentar en `2_tech_go_live_tasks.md`.

### 2.4 Certificados: UI visible vs. feature deshabilitada
| Documento | Afirmación |
|-----------|-----------|
| `0_matriz_cobertura.md` | "hay UI activa (`/certificates`)" |
| `1_feature_flags_UC7_UC10_post_mvp.md` | Feature flag bloquea ruta |
| `go_live_status.md` | "/certificates devuelve 404" |

**Resolución**: La UI está correctamente bloqueada por feature flag. Eliminar mención de "UI activa" en la matriz para evitar confusión.

---

## 3. Bloqueantes críticos (resolver antes de deploy)

### 3.1 Working tree DIRTY
- **Estado**: `go_live_status.md` reporta cambios locales pendientes
- **Impacto**: Bloquea release reproducible
- **Acción**: `git status`, resolver cambios, crear commit limpio
- **Responsable**: DevOps
- **Esfuerzo**: 1h

### 3.2 Evidencia funcional faltante para ASYNC_GCS
- **Estado**: Tests pasan pero falta corrida real en entorno objetivo
- **Impacto**: UC-F08/F09/F11/F13 no pueden habilitarse sin evidencia
- **Acción**: Ejecutar pipeline completo por cada UC en staging
- **Responsable**: Backend
- **Esfuerzo**: 4-8h

---

## 4. Matriz de cobertura actualizada

| UC | Nombre actualizado | Estado | Habilitación |
|----|-------------------|--------|--------------|
| UC-F01 | Contacto y soporte | ✅ VERDE | MVP_CORE |
| UC-F02 | Estadísticas públicas | ✅ VERDE | MVP_CORE |
| UC-F03 | Histórico de incendios | 🟡 AMARILLO | MVP_CORE |
| UC-F04 | Calidad del dato | ✅ VERDE | MVP_CORE |
| UC-F05 | Recurrencia y tendencias | 🟡 AMARILLO | MVP_CORE |
| UC-F06 | Verificar terreno | ✅ VERDE | MVP_CORE |
| UC-F07 | Registro visitantes offline | N/A | Post-MVP |
| UC-F08 | Carrusel satelital | 🟡 AMARILLO | ASYNC_GCS |
| UC-F09 | Reporte de cierre | 🟡 AMARILLO | ASYNC_GCS |
| UC-F10 | Certificación legal | N/A | Post-MVP |
| UC-F11 | Reportes especializados | 🟡 AMARILLO | ASYNC_GCS |
| UC-F12 | Recuperación VAE | 🟡 AMARILLO | Post-MVP |
| UC-F13 | Agrupación macro | 🟡 AMARILLO | ASYNC_GCS |

---

## 5. Tareas técnicas por prioridad

### Prioridad 1: Bloqueantes para MVP_CORE

| # | Tarea | UC | Tipo | Esfuerzo | Estado |
|---|-------|----|----- |----------|--------|
| T01 | Limpiar working tree y crear release-candidate | Infra | DevOps | 1h | ⛔ Pendiente |
| T02 | Actualizar `0_matriz_cobertura.md` con correcciones | Docs | Doc | 30m | ⛔ Pendiente |
| T03 | Ejecutar smoke readonly UC-F05 en staging | UC-F05 | Test | 2h | ⛔ Pendiente |
| T04 | Adjuntar evidencia de performance UC-F03 | UC-F03 | Test | 1h | ⛔ Pendiente |

### Prioridad 2: Habilitación de ASYNC_GCS

| # | Tarea | UC | Tipo | Esfuerzo | Estado |
|---|-------|----|----- |----------|--------|
| T05 | Ejecutar worker de refresh satelital real | UC-F08 | Worker | 2h | ⛔ Pendiente |
| T06 | Verificar `slides_data` poblado en fire_events | UC-F08 | DB | 30m | ⛔ Pendiente |
| T07 | Ejecutar task de closure report en evento test | UC-F09 | Worker | 2h | ⛔ Pendiente |
| T08 | Verificar idempotencia y lifecycle de artefactos | UC-F09 | Test | 1h | ⛔ Pendiente |
| T09 | Validar cola asíncrona E2E con GCS | UC-F11 | Test | 2h | ⛔ Pendiente |
| T10 | Ejecutar pipeline de clustering programado | UC-F13 | Worker | 2h | ⛔ Pendiente |

### Prioridad 3: Mejoras UX/UI (no bloqueantes)

| # | Tarea | UC | Tipo | Esfuerzo | Estado |
|---|-------|----|----- |----------|--------|
| T11 | Verificar implementación "Verificar terreno" | UC-F06 | Frontend | 1h | ⛔ Pendiente |
| T12 | Revisar nomenclatura consistente en navbar | UC-F06 | Frontend | 30m | ⛔ Pendiente |

---

## 6. Dependencias entre tareas

```
T01 ─────────────────────────────────────────► Deploy MVP_CORE
        │
        ├── T02 (docs)
        │
        ├── T03 ──► T04 ──► Evidencia UC-F03/F05
        │
        └── T05 ──► T06 ─┐
                         │
            T07 ──► T08 ─┼──► Evidencia ASYNC_GCS ──► Deploy ASYNC_GCS
                         │
            T09 ─────────┤
                         │
            T10 ─────────┘
```

---

## 7. Criterios de aceptación por perfil

### MVP_CORE
1. [ ] T01 completada (commit limpio)
2. [ ] T03 y T04 completadas (evidencia de performance)
3. [ ] `scripts/go_live_smoke.ps1` exit code 0
4. [ ] `scripts/ui_smoke.ps1` exit code 0
5. [ ] Feature flags UC-F07/UC-F10 verificados (404)

### ASYNC_GCS
1. [ ] Todos los criterios de MVP_CORE
2. [ ] T05-T10 completadas
3. [ ] `python scripts/test_gcs_conn.py` 3/3 buckets pass
4. [ ] Celery `inspect ping` → `pong`
5. [ ] Evidencia de `slides_data` poblado en al menos 1 fire_event

---

## 8. Estimación de esfuerzo total

| Prioridad | Esfuerzo total | Timeline sugerido |
|-----------|---------------|-------------------|
| P1 (bloqueantes MVP_CORE) | ~4.5h | Día 1 |
| P2 (habilitación ASYNC_GCS) | ~9.5h | Día 2-3 |
| P3 (mejoras UX no bloqueantes) | ~1.5h | Post-deploy |

**Total para GO con ASYNC_GCS**: ~14 horas de trabajo técnico

---

## 9. Archivos a actualizar post-resolución

1. `0_matriz_cobertura.md`: Corregir estado UC-F02, nomenclatura UC-F06
2. `2_tech_go_live_tasks.md`: Agregar sección de cronograma de workers
3. `go_live_status.md`: Actualizar con commit limpio y evidencias nuevas
4. `3_checklist_go_live.md`: Marcar ítems completados

---

## 10. Contactos y escalamiento

| Área | Responsable | Decisiones |
|------|-------------|-----------|
| Backend/Workers | TBD | T05-T10, bloqueantes técnicos |
| Frontend | TBD | T11-T12, verificación UX |
| DevOps | TBD | T01, deploy, infraestructura |
| Producto | TBD | GO/NO-GO final, priorización |

---

## Apéndice: Verificación de consistencia completada

| Archivo revisado | Inconsistencias | Estado |
|-----------------|-----------------|--------|
| 0_master_plan.md | 0 | ✅ |
| 0_matriz_cobertura.md | 2 | ⚠️ Requiere actualización |
| 1_feature_flags_UC7_UC10_post_mvp.md | 0 | ✅ |
| 2_tech_go_live_tasks.md | 1 | ⚠️ Requiere clarificación workers |
| 3_checklist_go_live.md | 0 | ✅ |
| go_live_status.md | 1 | ⚠️ Working tree dirty |
| razones_redisenio_*.md (4 archivos) | 0 | ✅ |
| old_audit_new_verify_land_tech_tasks.md | 0 | ✅ |