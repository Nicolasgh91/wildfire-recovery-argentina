# Frontend Docker Build Audit — ForestGuard

**Date**: 2026-02-17
**Target**: `frontend/Dockerfile` (React 19 + Vite 7 + TypeScript 5)
**Host**: Oracle Cloud Free Tier — 1 GB RAM, ARM64 (Ampere A1), Ubuntu

---

## 1. Symptoms

| Symptom | Evidence |
|---------|----------|
| VM freezes during `docker build` of frontend | Reported by team; 1 GB RAM VM with ~8 GB swap usage |
| Build silently "succeeds" but produces broken image | `Dockerfile:16` uses `\|\| true`, masking OOM kills (exit 137) |
| Frontend container nginx returns empty/404 | `Dockerfile` removes `default.conf` but provides no replacement |

---

## 2. Infrastructure Constraints

Source: `infrastructure_documentation.md`, `docker-compose.yml`

| Resource | Value |
|----------|-------|
| VM RAM | 1 GB |
| VM CPU | 1 OCPU (ARM64 Ampere A1) |
| OS | Ubuntu (Linux 4.4.0) |
| Docker services at runtime | 8+ (redis, api, 3 workers, celery-beat, flower, frontend, nginx) |
| Estimated runtime memory | 650–800 MB across all services |
| Available RAM during build | ~200–400 MB (with other services running) |

**Key insight**: Building the frontend inside Docker on this VM means Node.js competes with 8 running containers for 1 GB of RAM. Swap thrashing is inevitable.

---

## 3. Root Cause Analysis (Top 3)

### #1 — No Node.js heap limit (CRITICAL)

- **Evidence**: `frontend/Dockerfile:2` — `FROM node:20-alpine` with no `NODE_OPTIONS`
- **Impact**: V8's default heap limit on 64-bit is ~1.5 GB. On a 1 GB VM, this triggers swap thrashing → kernel OOM → build killed
- **Estimated peak**: 1.5 GB V8 heap + ~200 MB RSS overhead = ~1.7 GB total

### #2 — Sourcemaps enabled in production (HIGH)

- **Evidence**: `frontend/vite.config.ts:68` → `sourcemap: true`
- **Impact**: Rollup holds full AST + source mapping data in memory during bundling. This increases peak memory by 2–3x compared to `sourcemap: false`
- **Estimated impact**: +200–400 MB during Rollup bundling phase

### #3 — `|| true` masks OOM kills (MEDIUM)

- **Evidence**: `frontend/Dockerfile:16` → `RUN npx vite build --mode production || true`
- **Impact**: When Node.js is OOM-killed (`SIGKILL`, exit 137), Docker continues to the next stage and produces an image with empty/incomplete `dist/`. The build appears successful but the frontend serves nothing.

### Additional Contributing Factors

| Factor | Evidence | Impact |
|--------|----------|--------|
| Heavy dependency tree (79 prod + 22 dev) | `package.json` | `npm ci` alone can peak at 300–400 MB |
| `npx vite build` instead of `npm run build` | `Dockerfile:16` | Skips TypeScript compilation (correctness issue, not memory) |
| No nginx config in frontend container | `Dockerfile:23` removes `default.conf`, adds nothing | Frontend container is non-functional |
| Frontend not on `forestguard` network | `docker-compose.yml:231-243` — no `networks:` key | Networking isolation issue |
| `.dockerignore` incomplete | Missing `.git`, test tooling, Dockerfile itself | Larger build context → more I/O |

---

## 4. Dependency Analysis

### Heaviest bundled dependencies (by approximate size)

| Package | Approx. Bundle Size | Used For |
|---------|---------------------|----------|
| recharts (includes d3 subtree) | ~300 KB min+gz | Charts |
| framer-motion | ~120 KB min+gz | Animations |
| leaflet + react-leaflet | ~140 KB min+gz | Maps |
| @radix-ui/* (30+ components) | ~80 KB min+gz total | UI primitives |
| h3-js (WASM) | ~70 KB min+gz | Geospatial hexagons |
| @sentry/react | ~50 KB min+gz | Error tracking |
| @supabase/supabase-js | ~45 KB min+gz | Auth |
| i18next + react-i18next | ~40 KB min+gz | Internationalization |
| react + react-dom | ~130 KB min+gz | Core framework |

### Tree-shaking observations

- `lucide-react`: Tree-shakeable (individual icon imports) — **OK**
- `date-fns`: Tree-shakeable (individual function imports) — **OK**
- `@radix-ui/*`: Individual packages, each tree-shakeable — **OK**
- Barrel exports in `src/services/endpoints/index.ts` and `src/components/map/index.ts` — **Low risk**: Vite handles re-exports well for side-effect-free modules
- `@tanstack/react-query-devtools` is in `dependencies` (not `devDependencies`) — Has built-in production stripping, but inflates `npm ci` install time

### Lazy loading

All 21 pages use `React.lazy()` with dynamic imports — **Good**. No additional lazy-loading changes needed.

---

## 5. Dockerfile Analysis (Before)

```dockerfile
# PROBLEMS ANNOTATED
FROM node:20-alpine as build           # No NODE_OPTIONS → V8 uses up to 1.5 GB
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci                              # OK: uses npm ci, not npm install
COPY . .
RUN npx vite build --mode production || true  # || true masks OOM; npx skips tsc

FROM nginx:alpine
RUN rm /etc/nginx/conf.d/default.conf   # Removes config but adds nothing → broken
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

---

## 6. Vite Config Analysis (Before)

```typescript
build: {
  sourcemap: true,                    // PROBLEM: 2-3x memory during bundling
  chunkSizeWarningLimit: 500,
  rollupOptions: {
    output: {
      manualChunks: {
        'vendor-react': [...],        // 5 chunks configured — good start
        'vendor-map': [...],
        'vendor-charts': [...],
        'vendor-ui': [...],
        'vendor-query': [...],
      },
    },
  },
}
```

Missing: `framer-motion`, `i18next`, `h3-js` not in manual chunks → bundled into main chunk → larger peak memory per chunk.

---

## 7. Build Attempt Results

### Attempt 1 — `--max-old-space-size=512` (FAILED)

```
[build 6/6] RUN npx vite build --mode production         319.4s

Mark-Compact (reduce) 508.6 (521.3) -> 507.0 (521.3) MB,
  4072.27 / 0.00 ms  (average mu = 0.186, current mu = 0.196)
Mark-Compact (reduce) 508.1 (521.3) -> 507.1 (521.3) MB,
  4407.53 / 0.00 ms  (average mu = 0.105, current mu = 0.024)

FATAL ERROR: Ineffective mark-compacts near heap limit
  Allocation failed - JavaScript heap out of memory
```

**Analysis**: GC hit 508 MB with zero reclaimable memory. The working set
during Vite's transform phase genuinely needs ~600–700 MB for this project's
79 prod dependencies + 500 source files. 512 MB is too low.

### Root cause refinement

The initial 512 MB estimate was based on typical Vite projects. This project
has an unusually heavy transform workload:
- 79 production dependencies (including d3 subtree via recharts, WASM via h3-js)
- `@sentry/vite-plugin` loaded via static import (~20–50 MB wasted in Docker)
- `npx` spawns extra Node.js process (~30–50 MB overhead)

### Corrected approach

| Fix | Detail | Memory saved |
|-----|--------|-------------|
| Raise heap to 1024 MB | 30% GC headroom over 700 MB working set | Allows completion |
| Dynamic Sentry import | `await import()` only when env vars are set | ~20–50 MB in Docker |
| Direct `./node_modules/.bin/vite` | Skip `npx` process overhead | ~30–50 MB |

---

## 8. Changes Applied

### Round 1: Dockerfile + .dockerignore + nginx + Vite config

| File | Change |
|------|--------|
| `frontend/Dockerfile` | `NODE_OPTIONS=--max-old-space-size=1024`, removed `\|\| true`, `--ignore-scripts` on `npm ci`, `GENERATE_SOURCEMAP=false`, `COPY nginx.conf`, direct `./node_modules/.bin/vite` instead of `npx` |
| `frontend/nginx.conf` | Created: SPA routing, gzip, asset caching, deny hidden files |
| `frontend/.dockerignore` | Expanded: `.git`, test tooling, docs, Docker files, `.env.*` |
| `docker-compose.yml` | Added `networks: [forestguard]` and `mem_limit: 64m` to frontend service |
| `frontend/vite.config.ts` | `sourcemap` controlled by `GENERATE_SOURCEMAP` env var; `@sentry/vite-plugin` changed to dynamic import; added 3 new vendor chunks (`vendor-motion`, `vendor-i18n`, `vendor-geo`); added conditional `rollup-plugin-visualizer` |
| `frontend/package.json` | Added `rollup-plugin-visualizer` devDep; added `build:visualize` script |

### Round 2: CI build pipeline (strategic)

| File | Change |
|------|--------|
| `.github/workflows/frontend-build.yml` | Created: builds ARM64 image in CI, pushes to GHCR on main/develop |
| `docker-compose.override.yml` | Created: local dev override to build from Dockerfile instead of pulling |

---

## 9. Expected Results (Comparative)

| Metric | Before (original) | After (on-VM, 1024 MB) | After (CI build) |
|--------|-------------------|------------------------|-------------------|
| Node.js V8 heap ceiling | ~1.5 GB (default) | 1024 MB (hard cap) | N/A (CI has 7 GB) |
| Peak build memory on VM | ~1.5–2 GB (swap thrash) | ~1.1 GB (bounded swap) | 0 (pull only, ~30 MB) |
| Build time on VM | Freezes / OOM killed | ~2–4 min (swap-bound) | ~20s (docker pull) |
| Sourcemaps in prod image | Yes (2–3x memory) | No (conditional) | No |
| `dist/` after build | Empty/broken (\|\| true) | Complete (fails loudly on OOM) | Complete (built in CI) |
| Image size (final) | ~20 MB (nginx:alpine + dist) | ~20 MB | ~20 MB |
| Frontend nginx | Broken (no server block) | Working SPA routing | Working SPA routing |
| OOM detection | Silent | Loud (exit 137 fails build) | N/A |

---

## 10. Verification Checklist

Run these commands on the VM after deploying changes:

```bash
# 0. IMPORTANT: stop other services first to free RAM for the build
docker compose stop

# 1. Build context size (should be < 5 MB)
docker compose build --no-cache frontend 2>&1 | head -3

# 2. Build completes without OOM
time docker compose build --no-cache frontend
# Exit code should be 0, no "Killed" in output

# 3. No source maps in production image
docker run --rm forestguard-frontend find /usr/share/nginx/html -name "*.map" | wc -l
# → 0

# 4. Vendor chunks present (should show 8 vendor-* files)
docker run --rm forestguard-frontend ls /usr/share/nginx/html/assets/ | grep vendor-

# 5. SPA routing works
docker run --rm -d -p 8888:80 --name fg-test forestguard-frontend
curl -s -o /dev/null -w "%{http_code}" http://localhost:8888/
# → 200
curl -s -o /dev/null -w "%{http_code}" http://localhost:8888/some/spa/route
# → 200 (SPA fallback)
docker stop fg-test

# 6. Nginx config valid
docker run --rm forestguard-frontend nginx -t
# → "syntax is ok"

# 7. Image size
docker images forestguard-frontend --format "{{.Size}}"
# → should be < 50 MB

# 8. Memory during build (in separate terminal)
watch -n 0.5 'free -m'
# Peak "used" should stay under ~900 MB on 1 GB VM

# 9. Gzip compression works
docker run --rm -d -p 8888:80 --name fg-test forestguard-frontend
curl -s -H "Accept-Encoding: gzip" -D- http://localhost:8888/ | grep -i content-encoding
# → "Content-Encoding: gzip"
docker stop fg-test
```

---

## 11. Known Issues (Out of Scope)

1. **Nginx reverse proxy architecture**: The root-level `nginx.conf` serves from its own filesystem (`root /usr/share/nginx/html`), not from the frontend container. To fix: change to `proxy_pass http://frontend:80;` in `location /`.

2. **1.8 MB hero image** (`src/assets/bosque_landing.jpeg`): Gets processed by Vite during build. Converting to WebP/AVIF could reduce both build memory and output size. Minor impact compared to other fixes.

3. **`@tanstack/react-query-devtools`** in `dependencies` instead of `devDependencies`: Has built-in production stripping, so not a runtime issue, but inflates `npm ci` install time.

---

## 12. Long-Term Recommendation

For a 1 GB VM, **building any modern Node.js application inside Docker is operating at the edge of feasibility**. The recommended long-term strategy is:

1. **Use the GitHub Actions CI workflow** (PR3) to build the frontend image in CI (7 GB RAM runners)
2. **Pull the pre-built image** on the VM via `docker compose pull frontend`
3. **Remove `docker-compose.override.yml`** on the production VM so it uses the pre-built image
4. The local build path (PR1+PR2 optimizations) remains as a fallback for development

This eliminates the risk of OOM entirely and reduces deploy time from 60–90s to ~20s.
