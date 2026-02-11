import { sentryVitePlugin } from "@sentry/vite-plugin";
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig(async () => {
  const plugins = [
    react(),
    sentryVitePlugin({
      org: "freelnace",
      project: "javascript-react"
    }),
    sentryVitePlugin({
      org: "freelnace",
      project: "javascript-react"
    })
  ]

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
      exclude: ['tests/ui/**', '**/playwright-report/**', '**/test-results/**'],
    },

    build: {
      sourcemap: true
    }
  }
})
