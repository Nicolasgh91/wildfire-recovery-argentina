# Changelog de Documentación — ForestGuard

## 2026-02-15 — Auditoría y Reorientación Integral de Documentación

### Cambio estratégico

Reorientación del framing del proyecto:
- **Antes**: "Plataforma de inteligencia geoespacial para la fiscalización legal y monitoreo de recuperación"
- **Después**: "Plataforma full-stack de inteligencia geoespacial que centraliza y expone de forma transparente datos satelitales públicos dispersos sobre incendios forestales en Argentina"

El eje del proyecto pasa de "enforcement legal" a "acceso transparente y exploración de información pública satelital".

---

### Archivos modificados

#### `README.md`
- Reescritura completa del archivo
- Nueva tagline sin referencia a "fiscalización legal"
- Nueva sección: **"Sobre este proyecto"** — contexto personal (primera app full-stack, primera API, proyecto de aprendizaje en producción)
- Nueva sección: **"Qué demuestra este proyecto"** — autonomía técnica, capacidad arquitectónica, pensamiento sistémico, decisiones de costo cero
- Nueva sección: **"Qué aprendí construyendo esto"** — lecciones técnicas concretas (async-first, reproducibilidad satelital, RLS, free tiers, H3, circuit breakers, service layer)
- Sección "Descripción" reorientada: de "evidencia legal verificable" a "información estructurada, verificable y accesible"
- "Fiscalización legal" → "Verificación de terreno" en características
- "Certificados legales verificables" → "Certificados verificables"
- "Reportes judiciales" → "Reportes técnicos" en descripciones
- Casos de uso reducidos a tabla resumen con link a `docs/use_cases.md`
- Roadmap actualizado con items completados
- Stack tecnológico actualizado (React 19, TypeScript, Leaflet, TanStack Query, i18next)
- Tabla de workers especializados agregada (ingestion, clustering, analysis)
- Sección de fuentes de datos expandida (IGN/APN)

#### `frontend/src/data/translations.ts`

**Sección Manual (ES + EN):**
- `manualSectionLegalAudit`: "Auditoría Legal" → "Verificación de terreno" / "Legal Audit" → "Land Verification"
- `manualMainNav3`: Reorientado de "restricciones legales" a "historial de incendios y evolución del suelo"
- `manualAuditP1`: Reescrito completamente — de herramienta de auditoría legal a herramienta de exploración
- `manualAuditHowToTitle`: "Cómo realizar una auditoría" → "Cómo verificar un terreno" / "How to run an audit" → "How to verify land"
- `manualAuditHowTo3`: "Ejecutar Auditoría" → "Verificá" / "Run Audit" → "Verify"
- `manualAuditHowTo4`: Expandido para incluir vegetación y evidencia visual
- Nuevas claves agregadas: `manualSectionEpisodes`, `manualEpisodesP1`, `manualEpisodesP2`, `manualEpisodesHowTitle`, `manualEpisodesHow1-3` (ES + EN)

**Sección FAQ:**
- `faqA4` (ES + EN): "Nuestra herramienta de Auditoría Legal" → "La herramienta de verificación de terreno"
- 6 nuevas preguntas/respuestas agregadas (ES + EN):
  - Q6: Origen de los datos (NASA FIRMS, GEE, Open-Meteo, IGN/APN)
  - Q7: Generación de imágenes satelitales (GEE on-demand)
  - Q8: Responsabilidad legal (no, herramienta de exploración)
  - Q9: Imágenes no disponibles/con nubes (limitación óptica Sentinel-2)
  - Q10: Financiamiento del proyecto (costo cero, free tiers)
  - Q11: Latencia de detecciones (3-12h satelital, 12h ingesta)

**Sección Glossary (ES + EN):**
- `glossaryTermLandAudit`: "Auditoría de Uso del Suelo" → "Verificación de Uso del Suelo" / "Land-Use Audit" → "Land-Use Verification"
- `glossaryDefLandAudit`: Reorientado de "verificación del cumplimiento" a "consulta que cruza ubicación con datos históricos"

#### `frontend/src/pages/manual.tsx`
- Agregada sección "Episodios" (6ta sección) al array `manualSections`
- Import agregado: `Layers` de lucide-react
- Sigue el patrón exacto de las secciones existentes

#### `frontend/src/pages/faq.tsx`
- 6 nuevas entradas agregadas al array `faqItems` (Q6-Q11)

---

### Archivos creados

#### `docs/use_cases.md`
- Documentación expandida de 10 casos de uso implementados (UC-F01 a UC-F13)
- Cada UC incluye: estado, descripción detallada, fuentes de datos, endpoints, servicios y workers involucrados
- UC-F06 renombrado: "Auditoría legal" → "Verificación de terreno"
- UC-F11 renombrado: "Reportes judiciales" → "Reportes técnicos verificables"
- Sección de casos de uso planificados (UC-F07, UC-F10, UC-F12)

#### `CHANGELOG_DOCUMENTATION.md`
- Este archivo

---

### Resumen de cambios terminológicos

| Antes | Después | Archivos |
|-------|---------|----------|
| Fiscalización legal | Eliminado/reemplazado | README.md |
| Auditoría Legal (título sección manual) | Verificación de terreno / Land Verification | translations.ts |
| Auditoría de Uso del Suelo (glossary) | Verificación de Uso del Suelo / Land-Use Verification | translations.ts |
| Ejecutar Auditoría (botón manual) | Verificá / Verify | translations.ts |
| Cómo realizar una auditoría | Cómo verificar un terreno / How to verify land | translations.ts |
| Reportes judiciales (título UC) | Reportes técnicos verificables | README.md, docs/use_cases.md |
| Certificados legales verificables | Certificados verificables | README.md |
| evidencia legal verificable | evidencia verificable | README.md |

---

### No modificado (por diseño)

- **Código backend**: Comentarios en `app/models/`, `app/services/`, `app/api/` sin cambios
- **Endpoints API**: Todos los paths (`/api/v1/audit/land-use`, etc.) sin cambios
- **Claves de traducción**: Solo se cambiaron valores, nunca nombres de claves (ej: `manualSectionLegalAudit` sigue siendo la clave, pero su valor cambió)
- **Documentos internos**: `review/`, `episode_creation_flow/`, `changes/` sin cambios
- **Scripts**: `scripts/` sin cambios
- **Tests**: Sin modificaciones (snapshots en `test-results/` se actualizarán al re-ejecutar tests)
- **Archivos de configuración**: `docker-compose.yml`, `.env.template`, `Dockerfile.*` sin cambios
