# Tareas técnicas — Open Graph, Twitter Card y favicon

> Objetivo: agregar metadatos de previsualización social (Open Graph + Twitter Card) y actualizar el favicon del sitio `huelladelfuego.com.ar`.  
> Capa: UI únicamente. No requiere cambios en backend, workers ni schema.  
> Prerequisito: tener disponibles los archivos de imagen antes de ejecutar las tareas de código.

---

## Decisiones fijadas

### D-01 — Ubicación de los assets

Los archivos de imagen deben colocarse en `frontend/public/`, **no** en `frontend/src/assets/`.  
Motivo: Vite copia `public/` a `dist/` sin hashing de nombre, lo cual es obligatorio para que las URLs absolutas en las etiquetas `<meta>` sean estables.

### D-02 — URL base en og:image

Usar URL absoluta con dominio de producción: `https://huelladelfuego.com.ar/og-image.jpg`.  
Las rutas relativas no son resueltas por la mayoría de scrapers sociales (WhatsApp, LinkedIn, Slack, Twitter/X).

### D-03 — Versionado de la imagen OG

Si la imagen OG se reemplaza en el futuro, usar un nuevo nombre de archivo (ej.: `og-image-v2.jpg`) en lugar de sobreescribir el existente. Cloudflare Pages cachea assets estáticos agresivamente; cambiar el nombre fuerza una URL nueva y evita que los scrapers sirvan la versión vieja.

### D-04 — Locale

Usar `og:locale = es_AR` (español de Argentina).

---

## Assets requeridos (preparar antes de ejecutar el código)

| Archivo | Dimensiones | Formato | Notas |
|---------|-------------|---------|-------|
| `og-image.jpg` | 1200 × 630 px | JPG o PNG | Imagen de previsualización social. Debe funcionar con fondo oscuro. Incluir logo + nombre del sitio. |
| `favicon.ico` | 32 × 32 px (multires recomendado: 16, 32, 48) | ICO | Ícono para pestañas de navegador. |
| `favicon-192.png` | 192 × 192 px | PNG | Ícono para Android / PWA / Apple touch icon. |

Herramientas sugeridas para generación:
- Favicon ICO multires: [favicon.io](https://favicon.io) o [realfavicongenerator.net](https://realfavicongenerator.net)
- Imagen OG: Figma, Canva, o cualquier herramienta de diseño exportando a 1200×630

---

## Fase 1 — Agregar assets al repositorio

**Archivo destino**: `frontend/public/`

### Tarea 1.1 — Copiar los tres archivos de imagen

```
frontend/public/og-image.jpg        ← imagen Open Graph (1200×630)
frontend/public/favicon.ico         ← favicon multires
frontend/public/favicon-192.png     ← ícono 192×192
```

**Verificación**: ejecutar `ls frontend/public/` y confirmar que los tres archivos están presentes.

---

## Fase 2 — Modificar `index.html`

**Archivo**: `frontend/index.html`

### Tarea 2.1 — Reemplazar el bloque `<head>` existente

Localizar el bloque de favicon actual (normalmente una sola línea `<link rel="icon" ...>`) y reemplazarlo por el bloque completo siguiente.  
Si ya existen etiquetas `og:*` o `twitter:*`, eliminarlas antes de insertar el bloque nuevo para evitar duplicados.

**Bloque a insertar dentro de `<head>`, antes del cierre `</head>`:**

```html
<!-- Favicon -->
<link rel="icon" type="image/x-icon" href="/favicon.ico" />
<link rel="icon" type="image/png" sizes="192x192" href="/favicon-192.png" />
<link rel="apple-touch-icon" href="/favicon-192.png" />

<!-- Open Graph -->
<meta property="og:type" content="website" />
<meta property="og:url" content="https://huelladelfuego.com.ar/" />
<meta property="og:title" content="Huella del fuego" />
<meta property="og:description" content="Monitoreo satelital de incendios y recuperación de vegetación en Argentina." />
<meta property="og:image" content="https://huelladelfuego.com.ar/og-image.jpg" />
<meta property="og:image:width" content="1200" />
<meta property="og:image:height" content="630" />
<meta property="og:locale" content="es_AR" />
<meta property="og:site_name" content="Huella del fuego" />

<!-- Twitter Card -->
<meta name="twitter:card" content="summary_large_image" />
<meta name="twitter:title" content="Huella del fuego" />
<meta name="twitter:description" content="Monitoreo satelital de incendios y recuperación de vegetación en Argentina." />
<meta name="twitter:image" content="https://huelladelfuego.com.ar/og-image.jpg" />
```

**Verificación**: abrir `index.html` y confirmar que no hay etiquetas `og:*` o `twitter:*` duplicadas.

---

## Fase 3 — Verificación local

### Tarea 3.1 — Build local

```bash
cd frontend
npm run build
```

Confirmar que el build termina sin errores y que `dist/` contiene:
- `dist/og-image.jpg`
- `dist/favicon.ico`
- `dist/favicon-192.png`
- `dist/index.html` con las etiquetas `og:*` presentes

### Tarea 3.2 — Preview local

```bash
npm run preview
```

Abrir `http://localhost:4173` en el navegador y verificar:
- El favicon nuevo aparece en la pestaña del navegador.
- Ver código fuente de la página (`Ctrl+U`) y confirmar que las etiquetas `og:image` apuntan a la URL de producción correcta.

---

## Fase 4 — Deploy y verificación en producción

### Tarea 4.1 — Hacer push a `main`

El workflow `frontend-build.yml` se ejecuta automáticamente y despliega a Cloudflare Pages.

### Tarea 4.2 — Verificar con herramientas externas

Una vez publicado, validar con:

| Herramienta | URL | Qué verifica |
|-------------|-----|-------------|
| Open Graph debugger | https://www.opengraph.xyz | Vista previa general OG |
| Facebook Sharing Debugger | https://developers.facebook.com/tools/debug/ | Facebook / WhatsApp |
| Twitter Card Validator | https://cards-dev.twitter.com/validator | Twitter/X |
| LinkedIn Post Inspector | https://www.linkedin.com/post-inspector/ | LinkedIn |

**Criterio de aceptación**: las cuatro herramientas muestran la imagen OG, el título y la descripción correctamente sin errores de parseo.

### Tarea 4.3 — Verificar favicon en producción

Abrir `https://huelladelfuego.com.ar` en Chrome, Firefox y Safari (o Safari iOS) y confirmar que el ícono nuevo aparece en la pestaña.

---

## Registro de decisiones

| ID | Decisión | Estado |
|----|----------|--------|
| D-01 | Assets en `public/`, no en `src/assets/` | Fijado |
| D-02 | URL absoluta en `og:image` | Fijado |
| D-03 | Versionado por nombre de archivo al reemplazar | Fijado |
| D-04 | `og:locale = es_AR` | Fijado |

---

## Estado de fases

| Fase | Descripción | Estado |
|------|-------------|--------|
| 1 | Assets en `public/` | ✅ Completado |
| 2 | Modificar `index.html` | ✅ Completado |
| 3 | Verificación local | ✅ Completado |
| 4 | Deploy y verificación producción | ⬜ Pendiente |
