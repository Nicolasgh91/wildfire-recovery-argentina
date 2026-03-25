import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'path'
import fs from 'fs'

function loadJson<T>(file: string, fallback: T): T {
  const p = path.resolve(__dirname, 'public', file)
  if (!fs.existsSync(p)) return fallback
  return JSON.parse(fs.readFileSync(p, 'utf-8')) as T
}

const ssgRoutes = loadJson<{
  static_routes: string[]
  province_routes: string[]
  zone_routes: string[]
  episode_routes: string[]
  total: number
}>('ssg-routes.json', {
  static_routes: ['/metodologia', '/acerca'],
  province_routes: [],
  zone_routes: [],
  episode_routes: [],
  total: 2,
})

const ssgSeoData = loadJson<{ episodes?: Record<string, unknown> }>('ssg-seo-data.json', {
  episodes: {},
})

const seoIndex: Record<string, unknown> = ssgSeoData.episodes ?? {}

export default defineConfig(async () => {
  const plugins = [react()]

  // Optional bundle visualization (generates dist/stats.html)
  if (process.env.VISUALIZE === 'true') {
    try {
      const { visualizer } = await import('rollup-plugin-visualizer')
      plugins.push(
        visualizer({
          filename: 'dist/stats.html',
          gzipSize: true,
          brotliSize: true,
        }) as any,
      )
    } catch (err) {
      console.warn('rollup-plugin-visualizer no está instalado; omitiendo análisis de bundle.')
    }
  }

  // Source maps: enabled locally for debugging, disabled in Docker/CI
  // to reduce Rollup memory usage by ~2-3x.
  // Set GENERATE_SOURCEMAP=false in Docker (or any memory-constrained env).
  const generateSourcemap = process.env.GENERATE_SOURCEMAP !== 'false'

  return {
    plugins,

    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },

    server: {
      proxy: {
        '/api': {
          target: 'http://localhost:8000',
          changeOrigin: true,
        },
      },
    },

    test: {
      environment: 'jsdom',
      globals: true,
      setupFiles: './src/test/setup.ts',
      include: ['src/**/*.{test,spec}.?(c|m)[jt]s?(x)'],
      exclude: [
        '**/node_modules/**',
        '**/dist/**',
        '**/build/**',
        '**/.*/**',
        'tests/ui/**',
        '**/playwright-report/**',
        '**/test-results/**',
      ],
    },

    build: {
      sourcemap: generateSourcemap,
      chunkSizeWarningLimit: 500,
      modulePreload: { polyfill: true },
      rollupOptions: {
        output: {
          manualChunks(id: string) {
            // 1. Leaflet y plugins — solo necesarios en rutas con mapa
            if (
              id.includes('node_modules/leaflet') ||
              id.includes('node_modules/react-leaflet') ||
              id.includes('node_modules/leaflet.glify') ||
              id.includes('node_modules/@react-leaflet')
            ) {
              return 'vendor-leaflet'
            }

            // 2. H3 — cálculos geoespaciales, solo en mapa/análisis
            if (id.includes('node_modules/h3-js')) {
              return 'vendor-h3'
            }

            // 3. Animaciones — Framer Motion, solo en componentes con transiciones
            if (id.includes('node_modules/framer-motion')) {
              return 'vendor-motion'
            }

            // 4. Componentes UI headless — Radix, Embla
            if (
              id.includes('node_modules/@radix-ui') ||
              id.includes('node_modules/embla-carousel')
            ) {
              return 'vendor-ui'
            }

            // 5. Datos y estado — React Query, Zustand o similar
            if (
              id.includes('node_modules/@tanstack') ||
              id.includes('node_modules/zustand')
            ) {
              return 'vendor-state'
            }

            // 5b. Supabase — auth, storage, realtime (solo cuando se usa)
            if (id.includes('node_modules/@supabase')) {
              return 'vendor-supabase'
            }

            // 5c. Forms — Zod, react-hook-form (solo en rutas con formularios)
            if (
              id.includes('node_modules/zod') ||
              id.includes('node_modules/react-hook-form') ||
              id.includes('node_modules/@hookform')
            ) {
              return 'vendor-forms'
            }

            // 6. React core — siempre se carga; separado para cache de larga duración
            if (
              id.includes('node_modules/react/') ||
              id.includes('node_modules/react-dom/') ||
              id.includes('node_modules/react-router') ||
              id.includes('node_modules/scheduler/')
            ) {
              return 'vendor-react'
            }

            // 7. i18n y geo extra (recharts sin manualChunk para cargar solo en rutas con gráficos)
            if (id.includes('node_modules/i18next') || id.includes('node_modules/react-i18next')) {
              return 'vendor-i18n'
            }
            if (id.includes('node_modules/h3-js')) {
              return 'vendor-geo'
            }

            // Dejar que el resto siga la estrategia de chunking por defecto
          },
        },
      },
    },

    ssgOptions: {
      script: 'async',
      formatting: 'minify',
      includedRoutes: () => [
        ...ssgRoutes.static_routes,
        ...ssgRoutes.province_routes,
        ...ssgRoutes.zone_routes,
        ...ssgRoutes.episode_routes,
      ],
      onBeforePageRender: async (route: string, _html: string, appCtx: any) => {
        const match = route.match(/^\/episodios\/(.+)$/)
        if (!match) return
        const slug = match[1]
        const data = seoIndex[slug]
        if (data && appCtx?.queryClient) {
          appCtx.queryClient.setQueryData(['episode-seo', slug], data)
        }
      },
    },
  }
})
