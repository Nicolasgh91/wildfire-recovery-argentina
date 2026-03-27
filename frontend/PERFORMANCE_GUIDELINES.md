# Performance & Quality Guidelines

Guía para mantener buenos scores de Lighthouse y evitar regresiones en futuras implementaciones.

---

## 1. Carga de fuentes

- La fuente **Inter** se carga localmente via `@fontsource-variable/inter` (importada en `index.css`). Esto elimina la dependencia de Google Fonts, mejora el TTFB de fuentes y reduce third-party requests.
- **Nunca** usar `@import url(...)` en archivos CSS para cargar fuentes externas; esto bloquea el renderizado.
- **Nunca** agregar `<link>` a Google Fonts en `index.html`. Si se necesita una nueva fuente, usar `@fontsource` o `@fontsource-variable`.
- Usar siempre `display: swap` (ya configurado en fontsource por defecto) para evitar FOIT (Flash of Invisible Text).
- Limitar los pesos de fuente a los estrictamente necesarios.
- Si por alguna razón se necesita cargar una fuente remota, usar:
  ```html
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link rel="preload" as="style" href="URL_DE_LA_FUENTE" onload="this.rel='stylesheet'">
  <noscript><link rel="stylesheet" href="URL_DE_LA_FUENTE"></noscript>
  ```

## 2. Code splitting y lazy loading

- **Todas las páginas** deben importarse con `React.lazy()` en el router.
- **Nunca** importar estáticamente librerías pesadas (leaflet, framer-motion, recharts, zod) en componentes que se cargan en el bundle principal.
- Si un componente solo se usa en ciertas rutas, asegurar que su import es lazy.
- **Componentes con tabs/acordeones**: el contenido de tabs no visibles por defecto debe cargarse con `React.lazy()` + `<Suspense>`. Esto difiere la carga de sus dependencias (ej: `zod`, `react-hook-form`) hasta que el usuario interactúa.
- Verificar con `pnpm build:visualize` que los chunks pesados no se incluyen en el entry point.

## 3. CSS con scope de ruta

- **Nunca** importar CSS de librerías externas (leaflet, etc.) en `main.tsx` o `index.css`. Importar en el componente raíz que lo necesita (ej: `BaseMap.tsx` importa `leaflet/dist/leaflet.css`).
- Los estilos específicos de mapa (`.fire-popup`, overrides de leaflet) están en `components/map/map-overrides.css`, importado solo por `BaseMap.tsx`.
- Esto evita que CSS de rutas específicas se incluya como render-blocking en todas las páginas.

## 4. Vendor chunks (vite.config.ts)

Al agregar una dependencia pesada (>20 KiB gzipped), considerar crear un chunk dedicado en `manualChunks`:

| Chunk | Contenido |
|-------|-----------|
| `vendor-react` | react, react-dom, react-router, scheduler |
| `vendor-leaflet` | leaflet, react-leaflet, leaflet.glify |
| `vendor-motion` | framer-motion |
| `vendor-ui` | @radix-ui/*, embla-carousel |
| `vendor-state` | @tanstack/*, zustand |
| `vendor-supabase` | @supabase/* |
| `vendor-forms` | zod, react-hook-form, @hookform/* |
| `vendor-i18n` | i18next, react-i18next |

Esto permite que el navegador cachee cada vendor independientemente y solo descargue lo necesario por ruta.

## 5. Librerías de animación

- **Preferir CSS nativo** (`@keyframes`, `transition`, `animation`) para efectos simples (fade-in, slide, gradient reveal, etc.). El componente `AnimatedGradientText` usa CSS `transition` puro sin dependencias.
- Solo usar `framer-motion` para animaciones complejas orquestadas (gestures, layout animations, drag), y siempre detrás de lazy imports.
- Nunca importar framer-motion en componentes que se renderizan en todas las páginas (ej: layout, navbar).

## 6. CSS

- Usar Tailwind classes que se purguen automáticamente. Evitar CSS global custom innecesario.
- Verificar que `tailwind.config.js` → `content` incluye todos los archivos con classes de Tailwind.
- Evitar `@apply` excesivo en `index.css`; preferir clases utilitarias directamente en JSX.
- CSS custom (como `.fire-popup`) debe estar acotado al componente que lo usa y en un archivo CSS separado dentro del directorio del componente.

## 7. Imágenes

- Formato preferido: **WebP** (o AVIF cuando sea posible).
- Siempre incluir `loading="lazy"` excepto para imágenes above-the-fold.
- Siempre incluir `width` y `height` explícitos (o aspect-ratio via CSS) para evitar CLS.
- Usar `decoding="async"` para imágenes que no son críticas.
- Para imágenes hero/above-the-fold en desktop, considerar `<link rel="preload" as="image">`.

## 8. Contraste y accesibilidad

- **Contraste mínimo WCAG AA**: 4.5:1 para texto normal, 3:1 para texto grande.
- **Fondos semi-transparentes**: Evitar `bg-white/80` o `bg-black/40` debajo de texto sin verificar contraste. Usar mínimo `bg-white/90` en light mode y `bg-black/60` en dark mode si hay texto encima.
- Usar `text-slate-800` como mínimo en fondos claros (no `text-slate-700`). En dark mode, usar `text-slate-200` como mínimo.
- Verificar contraste con herramientas: WebAIM Contrast Checker, axe DevTools, o Lighthouse.
- Todos los `<Link>` y `<button>` deben tener texto discernible o `aria-label`.
- Usar componentes Radix UI que ya proveen ARIA roles correctos.
- Verificar con Lighthouse o axe DevTools antes de cada release.
- No usar `tabindex > 0`.

## 9. Compresión

- El build genera archivos pre-comprimidos con **Brotli** (`.br`) y **Gzip** (`.gz`) en el Dockerfile.
- Nginx sirve las versiones pre-comprimidas via `brotli_static on` y `gzip_static on`.
- Brotli ofrece 15-25% más compresión que Gzip para assets de texto.
- Al cambiar la imagen base de Nginx, verificar que soporte el módulo `ngx_brotli`.

## 10. Security headers y CSP

Mantener actualizados los headers de seguridad en `frontend/nginx.conf`:

| Header | Valor |
|--------|-------|
| `Content-Security-Policy` | Actualizar `connect-src`, `script-src`, etc. al agregar nuevos orígenes |
| `X-Frame-Options` | `DENY` |
| `X-Content-Type-Options` | `nosniff` |
| `Cross-Origin-Opener-Policy` | `same-origin` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |

Al agregar un nuevo servicio externo (API, CDN, analytics), actualizar el CSP.

**Orígenes de terceros conocidos** que deben estar en el CSP:
- `https://challenges.cloudflare.com` y `https://static.cloudflareinsights.com` → `script-src`
- `https://cloudflareinsights.com` → `connect-src`
- `https://*.supabase.co` y `wss://*.supabase.co` → `connect-src`

**Limitaciones conocidas de terceros**:
- El script de Cloudflare (`cdn-cgi/challenge-platform/scripts/jsd/main.js`) usa APIs deprecadas (SharedStorage, StorageType.persistent, Fledge). Esto no se puede corregir desde nuestro lado y afecta el score de Best Practices.
- Los bloqueadores de ads pueden bloquear `static.cloudflareinsights.com/beacon.min.js` causando `ERR_BLOCKED_BY_CLIENT`. Esto es esperado y no requiere acción.

## 11. DevTools en producción

- **Nunca** incluir devtools en el bundle de producción.
- `ReactQueryDevtools` debe estar envuelto en `{import.meta.env.DEV && ...}` y cargado con `React.lazy()`.
- Lo mismo aplica para cualquier otra herramienta de debugging (Redux DevTools, etc.).

## 12. Cache

- Assets en `/assets/` con hash en el nombre: `Cache-Control: public, immutable` + `expires 1y`.
- `index.html`: `Cache-Control: no-cache, must-revalidate` para que siempre se revalide y cargue los assets más recientes.
- Scripts de terceros con TTL corto (ej: Cloudflare `main.js` con 4h): no se puede controlar desde nuestro lado.

## 13. SEO

- Toda nueva página debe usar el componente `<SEOHead>` con title, description y canonical.
- `index.html` debe tener `<meta name="description">` como fallback.
- `public/robots.txt` debe existir y ser un archivo de texto plano válido (no HTML).
- Mantener `<html lang="es">` correcto.
- Verificar que las rutas SSG incluyan las nuevas páginas en `ssg-routes.json`.

## 14. Third-party scripts

- Evaluar el impacto en performance antes de agregar cualquier script externo.
- Cargar scripts de terceros con `async` o `defer`.
- Usar `<link rel="preconnect">` para orígenes de terceros críticos (máximo 4).
- Evitar cargar scripts que solo se usan en ciertas páginas en el bundle global.

## 15. Checklist pre-deploy

Antes de cada release, verificar:

- [ ] `pnpm build` completa sin errores
- [ ] `pnpm build:budget` pasa los límites de tamaño de bundles
- [ ] Lighthouse score >= 90 en Performance, >= 95 en Accessibility
- [ ] No hay CSS de librerías importado en `main.tsx` (verificar con `grep -r "import.*css" src/main.tsx`)
- [ ] Contraste WCAG AA verificado en páginas con fondos semi-transparentes
- [ ] `robots.txt` es accesible y válido
- [ ] No hay errores en la consola del navegador (excluir Cloudflare beacon blocked)
- [ ] Security headers están presentes (verificar con securityheaders.com)
- [ ] CSP actualizado si se agregaron nuevos orígenes
- [ ] Nuevas páginas tienen `<SEOHead>` con metadata
- [ ] Imágenes nuevas usan WebP y tienen dimensiones explícitas
- [ ] DevTools no se incluyen en producción

---

> Este documento debe actualizarse cada vez que se descubra un nuevo patrón de regresión o se agregue una nueva categoría de optimización.
