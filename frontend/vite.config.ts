import { sentryVitePlugin } from '@sentry/vite-plugin'
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig(async () => {
  const plugins = [react()]

  const sentryAuthToken = process.env.SENTRY_AUTH_TOKEN
  const sentryOrg = process.env.SENTRY_ORG
  const sentryProject = process.env.SENTRY_PROJECT

  if (sentryAuthToken && sentryOrg && sentryProject) {
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
      const { default: critters } = await import('vite-plugin-critters')
      plugins.push(critters({ preload: 'swap', reduceInlineStyles: true }))
    } catch (err) {
      console.warn('vite-plugin-critters no está instalado; omitiendo extracción de CSS crítico.')
    }
  }

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
      sourcemap: true,
      chunkSizeWarningLimit: 500,
      rollupOptions: {
        output: {
          manualChunks: {
            'vendor-react': ['react', 'react-dom', 'react-router-dom'],
            'vendor-map': ['leaflet', 'react-leaflet'],
            'vendor-charts': ['recharts'],
            'vendor-ui': ['@radix-ui/react-dialog', '@radix-ui/react-popover', '@radix-ui/react-select', '@radix-ui/react-tabs', '@radix-ui/react-tooltip'],
            'vendor-query': ['@tanstack/react-query'],
          },
        },
      },
    }
  }
})
