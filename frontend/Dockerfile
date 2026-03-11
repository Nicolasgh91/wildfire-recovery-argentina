# ── Stage 1: Build ──────────────────────────────────────────────
FROM node:20-alpine AS build

# Constrain Node.js heap to 1024 MB.
# Vite 7 transform phase needs ~700 MB working set for this project.
# 512 MB proved insufficient (OOM at 508 MB during mark-compact GC).
# 1024 MB gives ~30% GC headroom.  On the 1 GB VM this will use swap
# (~200-400 MB) but stays bounded — unlike the default 1.5 GB which
# caused 8 GB of runaway swap thrashing.
ENV NODE_OPTIONS="--max-old-space-size=1024"

# Disable sourcemaps in Docker builds to reduce Rollup memory by ~2-3x.
ENV GENERATE_SOURCEMAP=false

# Skip critters plugin (not installed, but explicit is clearer).
ENV USE_CRITTERS=false

# Build-time frontend variables (must be provided by docker compose args).
ARG VITE_API_BASE_URL=/api/v1
ARG VITE_SUPABASE_URL
ARG VITE_SUPABASE_ANON_KEY
ARG VITE_API_KEY
ARG VITE_USE_SUPABASE_JWT=false
ARG VITE_AUTH_REDIRECT_URL=https://forestguard.freedynamicdns.org/auth/callback
ARG VITE_SITE_BASE_URL

ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
ENV VITE_SUPABASE_URL=${VITE_SUPABASE_URL}
ENV VITE_SUPABASE_ANON_KEY=${VITE_SUPABASE_ANON_KEY}
ENV VITE_API_KEY=${VITE_API_KEY}
ENV VITE_USE_SUPABASE_JWT=${VITE_USE_SUPABASE_JWT}
ENV VITE_AUTH_REDIRECT_URL=${VITE_AUTH_REDIRECT_URL}
ENV VITE_SITE_BASE_URL=${VITE_SITE_BASE_URL}

WORKDIR /app

# 1) Copy lockfiles first for layer caching
COPY package.json package-lock.json ./

# 2) Install ALL dependencies (dev deps needed for build tooling).
#    --ignore-scripts avoids postinstall scripts that may consume memory;
#    esbuild ships pre-built binaries so no postinstall is needed.
RUN npm ci --ignore-scripts

# 3) Copy source (filtered by .dockerignore)
COPY . .

# 4) Run Vite build — NO || true so OOM surfaces as build failure (exit 137).
#    We run vite directly (skipping tsc -b) because the Docker build only
#    needs the JS bundle; TypeScript checking runs in CI.
#    Use ./node_modules/.bin/ instead of npx to avoid spawning an extra
#    Node.js process (~30-50 MB overhead on a memory-constrained system).
RUN node ./scripts/validate-build-env.mjs
RUN ./node_modules/.bin/vite build --mode production

# ── Stage 2: Serve ──────────────────────────────────────────────
FROM nginx:alpine

# Remove default config and add SPA-compatible one
RUN rm /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built assets from stage 1
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
