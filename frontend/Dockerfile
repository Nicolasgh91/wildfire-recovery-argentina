# syntax=docker/dockerfile:1.7

FROM node:20-alpine AS deps
WORKDIR /app

# Evita descargar binarios de Cypress durante el build de producción.
ENV CYPRESS_INSTALL_BINARY=0

COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci --include=dev --no-audit --no-fund

FROM node:20-alpine AS build
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Build orientado a runtime estático: sin type-check extra ni sourcemaps por defecto.
ENV NODE_ENV=production
ENV VITE_BUILD_SOURCEMAP=false
RUN npm run build:docker

FROM nginx:1.27-alpine AS runtime
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
