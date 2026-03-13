## Historial de fixes de build (frontend)

### Fix 1 — Error Vite / `RecoveryPanel` (`isCanceledError`)

- **Síntoma**: el build de Vite fallaba en CI/Docker con:
  - `The symbol "isCanceledError" has already been declared` en `frontend/src/components/monitoring/RecoveryPanel.tsx`.
- **Causa**: helper local `function isCanceledError(error: unknown): boolean` que entraba en conflicto a nivel de bundler.
- **Fix aplicado**:
  - Renombrado del helper a `isErrCanceled` y actualización del uso:
    - Antes: `const canceled = isCanceledError(recoveryError)`.
    - Después: `const canceled = isErrCanceled(recoveryError)`.
- **Verificación**:
  - `cd frontend && npm run build` → build exitoso sin errores de Vite.
  - Job de GitHub Actions que ejecuta `vite build --mode production` dentro del Dockerfile del frontend pasa correctamente.

### Fix 2 — Impacto de F9 / F10 / F11 en el build

- **F9 (mapa y marcadores de violaciones)**:
  - Cambios en frontend (tipos de episodio, `MapPage`, `FireMarkers`) sin modificar el pipeline de build.
  - Verificado con `npm run build` tras los cambios.
- **F10 (página `/monitoring`)**:
  - Nueva página `MonitoringDashboard`, nuevo endpoint de cliente `getRecoverySummary`.
  - No introduce pasos adicionales de build; es código React/TS estándar.
  - `npm run build` sigue pasando con estos cambios.
- **F11 (backfill VAE)**:
  - Afecta únicamente workers/backend (`workers/tasks/recovery.py`, `workers/tasks/backfill.py`).
  - No cambia el proceso de build del frontend ni su Dockerfile.

### Estado actual

- `npm run build` en `frontend` compila correctamente (Vite + TypeScript).
- La GitHub Action que construye la imagen multi-arch del frontend (`vite build --mode production` en `frontend/Dockerfile`) pasa con éxito tras los fixes mencionados.

---

## Política de variables `VITE_*` en el frontend

### Clasificación por variable

| Variable              | Tipo                            | Uso principal                                              | Tratamiento actual |
|-----------------------|---------------------------------|------------------------------------------------------------|--------------------|
| `VITE_SUPABASE_URL`  | URL pública Supabase            | Inicializar cliente Supabase y API client                  | **Config pública de frontend** |
| `VITE_SUPABASE_ANON_KEY` | Anon key pública Supabase    | Cliente Supabase y fallback de `VITE_API_KEY` en API client| **Config pública de frontend (RLS obliga)** |
| `VITE_API_KEY`       | **Clave a auditar**             | Autenticación de llamadas desde frontend a backend/API     | **Pendiente de auditoría detallada**: hasta confirmar que sus permisos son equivalentes a la anon key (solo lectura / RLS), no se la clasifica como pública por defecto. |
| `VITE_AUTH_REDIRECT_URL` | URL de callback de auth      | Flujos de autenticación web/Android                        | **Config pública (no secreto)** |

### Regla de uso

- **Solo** las variables marcadas arriba como **config pública** pueden:
  - Exponerse vía `import.meta.env.VITE_*` en el código de frontend.
  - Aparecer como `ARG`/`ENV` en el `frontend/Dockerfile`.
- Cualquier credencial de mayor privilegio (por ejemplo):
  - `SUPABASE_SERVICE_ROLE_KEY`,
  - passwords de base de datos (`DB_PASSWORD`),
  - tokens de escritura o administración,
  - claves de acceso a servicios internos,
  
**tiene prohibido**:

- Entrar en el bundle de frontend.
- Aparecer en `.env` de frontend versionados.
- Ser pasada al build del frontend como `ARG/ENV` de Docker.

La política por defecto para credenciales de alto privilegio es: solo backend (FastAPI/workers) o BuildKit `--secret` en pipelines server-side cuando sea estrictamente necesario.

---

## Warnings de Docker sobre secretos en `ARG/ENV`

Durante el build de la imagen del frontend, Docker (y herramientas asociadas) emiten warnings del tipo:

- `SecretsUsedInArgOrEnv: Do not use ARG or ENV instructions for sensitive data (ARG "VITE_SUPABASE_ANON_KEY")`, etc.

### Por qué ocurren

- El `frontend/Dockerfile` define:
  - `ARG VITE_SUPABASE_URL`, `ARG VITE_SUPABASE_ANON_KEY`, `ARG VITE_API_KEY`, `ARG VITE_AUTH_REDIRECT_URL`, etc.
  - Y luego los mapea a `ENV` en el **stage de build** para que Vite pueda leerlos en tiempo de compilación.
- La regla de la herramienta es genérica: cualquier cosa llamada `*_KEY`, `*_TOKEN`, etc. en `ARG/ENV` se marca como sospechosa porque:
  - Los valores quedan visibles en el historial de capas (`docker history`).

### Decisión y aceptación de riesgo

- En este proyecto, las variables:
  - `VITE_SUPABASE_URL`,
  - `VITE_SUPABASE_ANON_KEY`,
  - `VITE_AUTH_REDIRECT_URL`,
  - y, **condicionada a auditoría**, `VITE_API_KEY`,
  
son **configuración pública de frontend** por diseño:

- Terminan embebidas en el bundle JS servido al cliente.
- No otorgan por sí mismas privilegios de escritura ni bypass de RLS (en el caso de anon keys).

Se **acepta explícitamente** que:

- Las capas intermedias de la imagen multi-arch del frontend contendrán estas variables, porque:
  - Ya son visibles para cualquier usuario que consuma la aplicación.
  - El verdadero control de acceso está en RLS/policies del backend, no en la «secrecía» de estas keys.

Regla futura:

- Si en algún momento se necesitara pasar una variable **realmente sensible** al proceso de build (service key, password, token de escritura, etc.), se deberá:
  - Usar **BuildKit `--secret`** en lugar de `ARG/ENV`, para evitar que el valor quede registrado en el historial de capas.
  - Y, preferentemente, re-evaluar si ese secreto debe participar del proceso de build o si puede limitarse a tiempo de ejecución en el backend.

---

## Detección de secretos reales en CI (gitleaks)

Para proteger contra la inclusión accidental de secretos reales en el repo (código, `.env`, docs), se adopta la siguiente política:

- **Herramienta recomendada**: gitleaks (o equivalente ya mencionado en la documentación de despliegue).
- **Alcance mínimo**:
  - Escanear todo el repositorio, con especial atención a:
    - `frontend/`,
    - archivos `.env*`,
    - `docs/` (donde a veces se pegan ejemplos o logs).
- **Objetivo**:
  - Detectar valores de:
    - JWTs,
    - Supabase service keys,
    - passwords,
    - tokens de alta entropía u otros patrones sensibles,
  - independientemente del **nombre** de la variable (es decir, aunque use un nombre inocuo como `VITE_BACKEND_TOKEN`).

Relación con los warnings de Docker:

- Los warnings de Docker (`SecretsUsedInArgOrEnv`) sirven como alerta por nombres sospechosos en `ARG/ENV`.
- gitleaks (u otra herramienta de valor) es el guardrail principal para detectar **valores** peligrosos en cualquier parte del repo.
- Ambos mecanismos se consideran complementarios, no excluyentes.

---

## Extensión a build Android / Capacitor

El roadmap del proyecto contempla builds móviles (Capacitor/Android). Para mantener coherencia de seguridad:

- Se aplica la **misma clasificación** de variables `VITE_*`:
  - Las variables consideradas **config pública** (tabla anterior) pueden usarse en la configuración de build Android (por ejemplo, `VITE_AUTH_REDIRECT_URL_ANDROID`, variantes de Supabase URL, etc.).
  - Variables de alto privilegio siguen prohibidas tanto en el bundle web como en el bundle móvil.
- Si en el futuro un flujo móvil necesitara acceso privilegiado:
  - La regla es la misma que en web: el acceso debe gestionarse por medio del backend (FastAPI) como proxy, nunca exponiendo claves de servicio directamente en el cliente.

Referencias:

- Ver documentos de init plan Android y despliegue móvil (p.ej. `docs/infrastructure/deployment/init_plan_android_play_store.md`) para alinear nombres concretos (`VITE_AUTH_REDIRECT_URL_ANDROID`, etc.) con esta política.

