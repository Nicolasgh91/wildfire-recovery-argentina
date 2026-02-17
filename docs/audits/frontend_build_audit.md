# Auditoría profunda del build del frontend (Docker + Vite/React)

## Alcance y limitaciones del entorno
- Se auditó el frontend en `frontend/` con evidencia de `Dockerfile`, `package.json`, `vite.config.ts`, `docker-compose.yml` y `.dockerignore`.
- En este entorno **no existe binario `docker`** (`bash: command not found: docker`), por lo tanto no fue posible ejecutar `docker build`, `docker history` ni medir layers reales aquí.
- También faltan en el repo los documentos mencionados como fuente de verdad (`frontend_documentation.md`, `infrastructure_documentation.md`, `project_roadmap.md`), por lo que la auditoría se basó exclusivamente en archivos existentes.

## Parte A — Reconstrucción y baseline medible

### A1) Dónde vive el frontend
- Carpeta: `frontend/`.
- Scripts y dependencias: `frontend/package.json`.
- Lockfile: `frontend/package-lock.json`.
- Node objetivo: no hay campo `engines`; README indica Node 18+.

### A2) Flujo de build actual (antes de cambios)
- `docker-compose.yml` define `frontend.build.context: ./frontend` con `dockerfile: Dockerfile`.
- Dockerfile original:
  - `COPY package.json package-lock.json ./`
  - `RUN npm ci`
  - `COPY . .`
  - `RUN npx vite build --mode production || true`
  - runtime sobre `nginx:alpine`.
- Hallazgo crítico: `|| true` en el paso de build ocultaba errores reales de compilación.

### A3) Baseline reproducible sin Docker (sustituto local)
> Debido a ausencia de Docker, se midió el mismo proceso de bundling con Vite localmente.

#### Baseline 1 (script de proyecto: `npm run build`)
- Resultado: falla de TypeScript (no llega a terminar bundling).
- Tiempo hasta fallo: `13s`.
- Memoria observada (`free -m` cada 1s): pico `1142 MB`.
- Error representativo: múltiples errores TS en `src/pages/FireHistory.tsx`, `src/services/api.ts` y tipado de `vite-plugin-critters`.

#### Baseline 2 (equivalente al Dockerfile viejo: `npx vite build --mode production` con sourcemap activo)
- Resultado: OK.
- Tiempo: `22s`.
- Memoria observada: pico `1909 MB`.
- Tamaño de salida `dist`: `14M` (incluye `.map`).

## Parte B — Causas raíz priorizadas (Top 3, con evidencia)

### 1) Sourcemaps de producción activados por defecto en Vite (impacto alto)
**Evidencia:** `build.sourcemap: true` en `frontend/vite.config.ts` (estado previo).
- Efecto medido:
  - `dist` pasa de `4.2M` (sin sourcemap) a `14M` (con sourcemap).
  - build de Vite pasa de `17.78s` (sin sourcemap) a `20.05s` (con sourcemap).
  - pico de memoria sube a ~`1.9 GB` en la corrida con sourcemaps.

### 2) Instalación de dependencias innecesariamente pesada para build de runtime (impacto alto)
**Evidencia:** en `frontend/package.json`, `cypress` y `@playwright/test` están en `devDependencies`; en Dockerfile viejo se hace `npm ci` sin controlar descarga de binarios de testing.
- Efecto esperado y mitigado:
  - más IO/red/espacio en build stage por toolchain E2E no usada para generar `dist`.
  - se añadió `CYPRESS_INSTALL_BINARY=0` para evitar ese costo en imagen de build.

### 3) Build no determinista y con errores enmascarados (`|| true`) (impacto medio-alto)
**Evidencia:** Dockerfile viejo ejecutaba `RUN npx vite build --mode production || true`.
- Consecuencia:
  - el pipeline puede reportar “éxito” aun cuando el frontend no buildée correctamente.
  - dificulta diagnosticar memoria/CPU porque los fallos quedan ocultos.

## Parte C — Correcciones implementadas

### PR (esta entrega) — Cambios de alto impacto / bajo riesgo
1. `frontend/Dockerfile`
   - Multi-stage explícito (`deps` → `build` → `runtime` nginx).
   - Cache de npm con BuildKit (`--mount=type=cache,target=/root/.npm`).
   - `CYPRESS_INSTALL_BINARY=0` para no descargar binarios E2E en build de producción.
   - reemplazo de comando por `npm run build:docker` (sin `|| true`).
   - `VITE_BUILD_SOURCEMAP=false` por defecto en el build de imagen.
2. `frontend/.dockerignore`
   - reforzado para excluir caches, artefactos de test (cypress/playwright), logs, `.env*`, VCS y temporales.
3. `frontend/package.json`
   - nuevo script `build:docker`: `vite build --mode production`.
4. `frontend/vite.config.ts`
   - sourcemaps ahora controlados por env var:
     - `VITE_BUILD_SOURCEMAP=true` => genera maps
     - default => sin maps
   - `minify: 'esbuild'` explícito.

## Parte D — Resultados cuantitativos (antes vs después)

> Métrica Docker/image/layers: pendiente de ejecutar en VM/CI con Docker disponible.

| Métrica | Antes (baseline equivalente) | Después (optimizado) | Cambio |
|---|---:|---:|---:|
| Build command | `VITE_BUILD_SOURCEMAP=true npx vite build --mode production` | `npm run build:docker` (`VITE_BUILD_SOURCEMAP=false`) | - |
| Tiempo build | 22s | 19s (log de npm) / 17.78s (log de Vite) | mejora |
| RAM pico (free -m) | 1909 MB | 1641 MB | **-268 MB** |
| `dist` size | 14M | 4.2M | **-70%** |
| Contexto docker (estimado por tar + .dockerignore) | 3,235,840 bytes | 3,225,600 bytes | leve mejora |
| OOM/freeze observado en esta sesión | no | no | sin cambios visibles |

## Parte E — Plan de optimización por fases

### Fase rápida (aplicable ya)
- Mantener sourcemaps OFF en producción de VM (`VITE_BUILD_SOURCEMAP=false`).
- Usar Dockerfile cache-friendly actual (deps separadas + cache npm).
- Mantener `CYPRESS_INSTALL_BINARY=0` en build stage de frontend.
- No ocultar errores (`|| true` prohibido en build).

### Fase estructural (si la VM Always Free sigue al límite)
1. **Build externo (CI) + deploy de imagen/artefacto**
   - Compilar en GitHub Actions (runner con más RAM).
   - Publicar imagen ya construida en registry.
   - En VM sólo hacer `docker pull` + `docker compose up -d`.
2. **Type-check fuera del Docker build de runtime**
   - Mantener `npm run build` (con `tsc`) en CI de calidad.
   - usar `build:docker` para bundling productivo reproducible.
3. **Reducir peso de dependencias en mediano plazo**
   - revisar uso de `lucide-react` y `date-fns` para imports más granulares.
   - analizar bundle con visualizer si se habilita como devDependency.

## Checklist de validación (comandos exactos)

### Sin Docker (repro local)
1. `cd frontend && npm ci`
2. `cd frontend && VITE_BUILD_SOURCEMAP=true npx vite build --mode production`
3. `cd frontend && npm run build:docker`
4. `cd frontend && du -sh dist`
5. `cd frontend && du -sh node_modules`
6. `cd frontend && du -sh node_modules/* | sort -hr | head -20`
7. `free -m` (en paralelo durante build) y/o `vmstat 1`

### Con Docker (ejecutar en VM destino)
1. `docker build --progress=plain -t fg-frontend:baseline -f frontend/Dockerfile.backup frontend`
2. `docker build --progress=plain -t fg-frontend:optimized -f frontend/Dockerfile frontend`
3. `docker image ls | grep fg-frontend`
4. `docker history fg-frontend:baseline --no-trunc`
5. `docker history fg-frontend:optimized --no-trunc`
6. `docker run --rm -d --name fg-front fg-frontend:optimized && docker stats fg-front`
7. `dmesg -T | tail -200`

