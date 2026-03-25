# Performance & Quality Guidelines

Guía para mantener buenos scores de Lighthouse y evitar regresiones en futuras implementaciones.

---

## 1. Carga de fuentes

- **Nunca** usar `@import url(...)` en archivos CSS para cargar fuentes externas; esto bloquea el renderizado.
- Cargar Google Fonts (u otras fuentes remotas) desde `index.html` con:
  ```html
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link rel="preload" as="style" href="URL_DE_LA_FUENTE" onload="this.rel='stylesheet'">
  <noscript><link rel="stylesheet" href="URL_DE_LA_FUENTE"></noscript>
  ```
- Usar siempre `display=swap` para evitar FOIT (Flash of Invisible Text).
- Limitar los pesos de fuente a los estrictamente necesarios.

## 2. Code splitting y lazy loading

- **Todas las páginas** deben importarse con `React.lazy()` en el router.
- **Nunca** importar estáticamente librerías pesadas (leaflet, framer-motion, recharts, zod) en componentes que se cargan en el bundle principal.
- Si un componente solo se usa en ciertas rutas, asegurar que su import es lazy.
- Verificar con `pnpm build:visualize` que los chunks pesados no se incluyen en el entry point.

## 3. Vendor chunks (vite.config.ts)

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

## 4. CSS

- Usar Tailwind classes que se purguen automáticamente. Evitar CSS global custom innecesario.
- Verificar que `tailwind.config.js` → `content` incluye todos los archivos con classes de Tailwind.
- Evitar `@apply` excesivo en `index.css`; preferir clases utilitarias directamente en JSX.
- CSS custom (como `.fire-popup`) debe estar acotado al componente que lo usa.

## 5. Imágenes

- Formato preferido: **WebP** (o AVIF cuando sea posible).
- Siempre incluir `loading="lazy"` excepto para imágenes above-the-fold.
- Siempre incluir `width` y `height` explícitos (o aspect-ratio via CSS) para evitar CLS.
- Usar `decoding="async"` para imágenes que no son críticas.
- Para imágenes hero/above-the-fold en desktop, considerar `<link rel="preload" as="image">`.

## 6. Security headers

Mantener actualizados los headers de seguridad en `frontend/nginx.conf`:

| Header | Valor |
|--------|-------|
| `Content-Security-Policy` | Actualizar `connect-src`, `script-src`, etc. al agregar nuevos orígenes |
| `X-Frame-Options` | `DENY` |
| `X-Content-Type-Options` | `nosniff` |
| `Cross-Origin-Opener-Policy` | `same-origin` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |

Al agregar un nuevo servicio externo (API, CDN, analytics), actualizar el CSP.

## 7. SEO

- Toda nueva página debe usar el componente `<SEOHead>` con title, description y canonical.
- `index.html` debe tener `<meta name="description">` como fallback.
- `public/robots.txt` debe existir y ser un archivo de texto plano válido (no HTML).
- Mantener `<html lang="es">` correcto.
- Verificar que las rutas SSG incluyan las nuevas páginas en `ssg-routes.json`.

## 8. Accesibilidad

- Contraste mínimo WCAG AA: **4.5:1** para texto normal, **3:1** para texto grande.
- Todos los `<Link>` y `<button>` deben tener texto discernible o `aria-label`.
- Usar componentes Radix UI que ya proveen ARIA roles correctos.
- Verificar con Lighthouse o axe DevTools antes de cada release.
- No usar `tabindex > 0`.

## 9. Third-party scripts

- Evaluar el impacto en performance antes de agregar cualquier script externo.
- Cargar scripts de terceros con `async` o `defer`.
- Usar `<link rel="preconnect">` para orígenes de terceros críticos (máximo 4).
- Evitar cargar scripts que solo se usan en ciertas páginas en el bundle global.

## 10. Checklist pre-deploy

Antes de cada release, verificar:

- [ ] `pnpm build` completa sin errores
- [ ] `pnpm build:budget` pasa los límites de tamaño de bundles
- [ ] Lighthouse score >= 80 en Performance, >= 90 en Accessibility
- [ ] `robots.txt` es accesible y válido
- [ ] No hay errores en la consola del navegador
- [ ] Security headers están presentes (verificar con securityheaders.com)
- [ ] Nuevas páginas tienen `<SEOHead>` con metadata
- [ ] Imágenes nuevas usan WebP y tienen dimensiones explícitas

---

> Este documento debe actualizarse cada vez que se descubra un nuevo patrón de regresión o se agregue una nueva categoría de optimización.
