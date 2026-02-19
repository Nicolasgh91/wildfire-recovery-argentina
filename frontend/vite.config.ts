import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig(async () => {
  const plugins = [react()]

  // Dynamic import: only load @sentry/vite-plugin when actually needed.
  // The static import was loading the entire Sentry module (~20-50 MB)
  // into memory even in Docker builds where SENTRY_* vars are never set.
  const sentryAuthToken = process.env.SENTRY_AUTH_TOKEN
  const sentryOrg = process.env.SENTRY_ORG
  const sentryProject = process.env.SENTRY_PROJECT

  if (sentryAuthToken && sentryOrg && sentryProject) {
    const { sentryVitePlugin } = await import('@sentry/vite-plugin')
    plugins.push(
      sentryVitePlugin({
        authToken: sentryAuthToken,
        org: sentryOrg,
        project: sentryProject,
      }),
    )
  }

  // Optional critical CSS extraction (no-op if plugin is not installed)
  if (process.env.USE_CRITTERS !== 'false') {
    try {
      // @ts-ignore
      const { default: critters } = await import('vite-plugin-critters')
      plugins.push(critters({ preload: 'swap', reduceInlineStyles: true }))
    } catch (err) {
      console.warn('vite-plugin-critters no está instalado; omitiendo extracción de CSS crítico.')
    }
  }

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
      rollupOptions: {
        output: {
          manualChunks: {
            'vendor-react': ['react', 'react-dom', 'react-router-dom'],
            'vendor-map': ['leaflet', 'react-leaflet'],
            'vendor-charts': ['recharts'],
            'vendor-ui': ['@radix-ui/react-dialog', '@radix-ui/react-popover', '@radix-ui/react-select', '@radix-ui/react-tabs', '@radix-ui/react-tooltip'],
            'vendor-query': ['@tanstack/react-query'],
            'vendor-motion': ['framer-motion'],
            'vendor-i18n': ['i18next', 'react-i18next'],
            'vendor-geo': ['h3-js'],
          },
        },
      },
    }
  }
})
