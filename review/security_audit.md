# Security Audit (MVP publicable)

Fecha: 2026-02-14

## Resumen ejecutivo

- Hallazgos críticos: 0
- Hallazgos altos: 3
- Hallazgos medios: 5
- Hallazgos bajos: 3
- Mitigaciones aplicadas en esta ejecución: 1 (PII en logs de contacto)

---

## 1) Autenticación / autorización

### ID: SEC-001
**Severidad:** media  
**Área:** frontend/backend  
**Evidencia:** `frontend/src/App.tsx` (rutas protegidas parciales, p.ej. `/audit` y `/fires/history` protegidas, `/reports` alias público hacia `/exploracion`) + `app/api/v1/reports.py` (endpoints sin JWT obligatorio en router)  
**Riesgo:** Existen flujos sensibles que están "protegidos por UI" o por convención de producto, pero no siempre por backend. Un cliente directo puede invocar endpoints sin pasar por `ProtectedRoute`.  
**Recomendación:** 1) Definir matriz de auth por endpoint en backend. 2) Aplicar dependencias JWT/API key explícitas en cada router sensible. 3) Mantener `ProtectedRoute` solo como UX, no como control de seguridad principal.  
**Estado:** pendiente

### ID: SEC-002
**Severidad:** media  
**Área:** backend  
**Evidencia:** `app/api/v1/fires.py#L96-L113` (`require_fire_access` permite JWT o API key, pero hay endpoints públicos en el mismo router con reglas heterogéneas)  
**Riesgo:** Heterogeneidad de reglas en un mismo módulo incrementa riesgo de errores de configuración y de cambios futuros inseguros.  
**Recomendación:** Separar claramente routers públicos/protegidos o aplicar política por prefijo + tests de autorización por endpoint.  
**Estado:** pendiente

---

## 2) Exposición de datos / RLS

### ID: SEC-003
**Severidad:** alta  
**Área:** db/infra  
**Evidencia:** `docs/architecture/roadmap_prod.md` sección 6.6 (historial de tablas sin RLS y verificación manual)  
**Riesgo:** Si RLS no está consistente por tabla y entorno, una mala policy puede exponer datos sensibles desde Supabase.  
**Recomendación:** Automatizar chequeo RLS en pipeline (query de auditoría + fail del deploy si tablas críticas carecen de RLS/policies esperadas).  
**Estado:** pendiente

---

## 3) Validación de inputs

### ID: SEC-004
**Severidad:** media  
**Área:** backend  
**Evidencia:** `app/api/v1/audit.py#L377-L383` (`q` en `/audit/search`), `app/api/v1/contact.py#L47-L53` (multipart), `app/api/v1/fires.py#L162-L165` (`search`, `page_size` opcional)  
**Riesgo:** Aunque hay validaciones básicas (longitud/rangos), no hay estrategia uniforme de límites de costo por endpoint (payload/query + cardinalidad de respuesta).  
**Recomendación:** Definir baseline de validación por dominio (search, geocoding, export, uploads) y cubrir con tests negativos comunes.  
**Estado:** pendiente

---

## 4) Secretos

### ID: SEC-005
**Severidad:** alta  
**Área:** infra  
**Evidencia:** archivo `.env` presente en raíz del workspace; `app/core/config.py#L22-L45` consume múltiples secretos de ejecución  
**Riesgo:** Riesgo de exposición accidental si `.env` se versiona o se comparte en artefactos de build.  
**Recomendación:** 1) Verificar `.gitignore` y reglas CI para bloquear `.env`. 2) Migrar secretos sensibles a secret manager del entorno. 3) Ejecutar escaneo de secretos en pre-commit y CI.  
**Estado:** pendiente

---

## 5) Logging

### ID: SEC-006
**Severidad:** alta  
**Área:** backend  
**Evidencia:** previo en `app/api/v1/contact.py` se registraba email completo en logs de aceptación  
**Riesgo:** PII en texto plano en logs (email) aumenta superficie de exposición por acceso a observabilidad, backups o exportaciones.  
**Recomendación:** Minimizar PII en logs (dominio o hash), estandarizar sanitización en middleware/logger.  
**Estado:** resuelto (cambio aplicado en `app/api/v1/contact.py` + test `tests/unit/test_contact.py`)

---

## 6) CORS / CSRF

### ID: SEC-007
**Severidad:** media  
**Área:** backend  
**Evidencia:** `app/main.py#L167-L174` (`allow_methods=["*"]`, `allow_headers=["*"]`) y `app/core/config.py#L78-L117` (orígenes por entorno)  
**Riesgo:** Aun con orígenes controlados, wildcard de métodos/headers puede ampliar innecesariamente la superficie ante configuraciones permisivas en entornos no productivos.  
**Recomendación:** Restringir métodos/headers a los usados por la API y documentar matriz CORS por ambiente.  
**Estado:** pendiente

---

## 7) Rate limiting / abuso

### ID: SEC-008
**Severidad:** alta  
**Área:** backend/infra  
**Evidencia:** `app/core/rate_limiter.py#L39-L46` (estado en memoria), `#L54-L65` (reset diario local), `#L54-L56` + uso general en endpoints públicos  
**Riesgo:** En despliegues multi-instancia, el rate limiting en memoria no es global y puede bypassearse distribuyendo requests entre réplicas.  
**Recomendación:** Migrar counters/bloqueos a Redis (o gateway) con claves por IP/user/endpoint y TTL explícito.  
**Estado:** pendiente

### ID: SEC-009
**Severidad:** media  
**Área:** backend  
**Evidencia:** `app/core/rate_limiter.py#L115-L120` (`X-Forwarded-For` tomado directamente)  
**Riesgo:** Si el servicio no está detrás de proxy confiable con sanitización, un atacante puede spoofear IP y evadir límites.  
**Recomendación:** Confiar en `X-Forwarded-For` solo desde proxies permitidos; caso contrario usar `request.client.host`.  
**Estado:** pendiente

---

## 8) Dependencias

### ID: SEC-010
**Severidad:** baja  
**Área:** backend/frontend  
**Evidencia:** `requirements.txt` con versiones fijas y mixtas sin reporte de auditoría adjunto  
**Riesgo:** Falta de evidencia periódica de CVEs deja ventanas de exposición no cuantificadas.  
**Recomendación:** Integrar `pip-audit` y `npm audit --omit=dev` (o herramienta equivalente) en CI, con baseline y SLA de remediación por severidad.  
**Estado:** pendiente

---

## 9) Headers de seguridad

### ID: SEC-011
**Severidad:** baja  
**Área:** backend  
**Evidencia:** No se observan middlewares explícitos para `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy`, `HSTS` en `app/main.py`  
**Riesgo:** Endurecimiento HTTP incompleto deja espacio a ataques de navegador y malas prácticas de embedding/referrer.  
**Recomendación:** Añadir middleware de security headers y validarlo con tests de respuesta.  
**Estado:** pendiente

---

## 10) Storage (GCS) / workers

### ID: SEC-012
**Severidad:** media  
**Área:** infra/workers  
**Evidencia:** `app/services/storage_service.py#L151-L168` (backend configurable con `local`), `app/core/config.py#L72-L75` (`STORAGE_BACKEND` default local), `docs/architecture/workers_documentation.md`  
**Riesgo:** Riesgo operativo de correr producción con backend local por configuración incorrecta, afectando disponibilidad, seguridad y trazabilidad de evidencias.  
**Recomendación:** Validación dura por entorno (`production` => bloquear `STORAGE_BACKEND=local`), healthcheck de storage obligatorio al startup y alertas.  
**Estado:** pendiente

---

## 11) CI/CD

### ID: SEC-013
**Severidad:** baja  
**Área:** infra  
**Evidencia:** `.github/workflows/*` presentes, sin evidencia en repo de gates obligatorios para secrets scan + dependency audit + authz contract tests  
**Riesgo:** Sin quality gates de seguridad, regresiones de auth/secretos/dependencias pueden llegar a ramas de release.  
**Recomendación:** Definir pipeline mínimo: lint + tests + escaneo secretos + auditoría dependencias + pruebas de autorización críticas.  
**Estado:** pendiente
